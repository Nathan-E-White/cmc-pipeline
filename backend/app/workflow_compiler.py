"""Compile admitted CMC case cards into an immutable, target-neutral workflow."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, ClassVar

SOLVER_IMAGE = "cmc-pipeline-v3-reference-solver@sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
R0_WORKFLOW = "r0-reference-field-export/v1"
_R0_CASES = frozenset(
    {
        "r0-elastic-displacement-e180-v1",
        "r0-elastic-displacement-e200-v1",
        "r0-elastic-displacement-e220-v1",
    }
)


@dataclass(frozen=True)
class AttemptPlan:
    run_id: str
    attempt_number: int
    case_card: dict[str, Any]
    workflow_key: str
    target: str
    declared_inputs: tuple[str, ...] = ()
    requested_resources: tuple[str, ...] = ("cpu",)
    retry_policy: str = "none"
    image_overrides: dict[str, str] | None = None


@dataclass(frozen=True)
class WorkflowStage:
    key: str
    depends_on: tuple[str, ...]
    image: str
    command: tuple[str, ...]
    input_roles: tuple[str, ...]
    output_roles: tuple[str, ...]
    resource_class: str
    failure_policy: str = "stop"
    execution_kind: str = "workload"
    adapter_service: str | None = None
    collector_profile: str | None = None
    mounts: tuple[str, ...] = ("/artifacts",)


@dataclass(frozen=True)
class CompiledWorkflow:
    workflow_key: str
    target: str
    stages: tuple[WorkflowStage, ...]
    inventory_digest: str
    canonical_inventory: bytes


@dataclass(frozen=True)
class WorkflowRefusal:
    reason: str
    subject: str


@dataclass(frozen=True)
class RenderedWorkflow:
    document: dict[str, Any]
    rendered_yaml: bytes
    inventory_digest: str


class WorkflowCompiler:
    """The catalog is the only authority for stages, images, adapters and collectors."""

    _stages: ClassVar[tuple[WorkflowStage, ...]] = (
        WorkflowStage(
            "mesh-audit",
            (),
            SOLVER_IMAGE,
            ("verify-case", "--output", "/artifacts"),
            ("declared-case-card",),
            ("mesh-audit",),
            "cpu",
            adapter_service="reference-solver",
        ),
        WorkflowStage(
            "reference-field-export",
            ("mesh-audit",),
            SOLVER_IMAGE,
            ("export-r0-field-case", "--output", "/artifacts"),
            ("declared-case-card",),
            (
                "field-set-manifest",
                "field/displacement/xdmf",
                "field/displacement/hdf5",
                "field/displacement/acceptance",
                "field/displacement/pair-map",
            ),
            "cpu",
            adapter_service="reference-solver",
        ),
        WorkflowStage(
            "collect-reference-field",
            ("reference-field-export",),
            SOLVER_IMAGE,
            ("collect", "reference-field/v1"),
            (
                "field-set-manifest",
                "field/displacement/xdmf",
                "field/displacement/hdf5",
                "field/displacement/acceptance",
                "field/displacement/pair-map",
            ),
            ("artifact-set-receipt",),
            "cpu",
            execution_kind="collector",
            collector_profile="reference-field/v1",
        ),
    )

    def compile(self, plan: AttemptPlan) -> CompiledWorkflow | WorkflowRefusal:
        if plan.workflow_key != R0_WORKFLOW:
            return WorkflowRefusal("unknown_workflow", plan.workflow_key)
        if plan.target not in {"compose", "hera"}:
            return WorkflowRefusal("target_ineligible", plan.target)
        if plan.retry_policy != "none" or plan.image_overrides:
            return WorkflowRefusal("mutable_execution_request", plan.workflow_key)
        if set(plan.declared_inputs) != {"declared-case-card"}:
            return WorkflowRefusal("undeclared_input", ",".join(plan.declared_inputs))
        if set(plan.requested_resources) != {"cpu"}:
            return WorkflowRefusal("unavailable_capability", ",".join(plan.requested_resources))
        case_id = plan.case_card.get("case_id")
        if case_id not in _R0_CASES:
            return WorkflowRefusal("invalid_r0_case_card", str(case_id))
        if any(key in plan.case_card for key in ("runner_key", "image", "command", "service")):
            return WorkflowRefusal("caller_selected_execution", str(case_id))
        stages = self._case_stages(str(case_id))
        if not self._valid_graph(stages):
            return WorkflowRefusal("invalid_dependency", plan.workflow_key)
        inventory = self._inventory(plan, stages)
        return CompiledWorkflow(
            plan.workflow_key, plan.target, stages, sha256(inventory).hexdigest(), inventory
        )

    def _case_stages(self, case_id: str) -> tuple[WorkflowStage, ...]:
        card_arg = ("--case-card", f"/opt/cmc/cases/{case_id}.json")
        return tuple(
            WorkflowStage(**{**asdict(stage), "command": (*stage.command, *card_arg)})
            if stage.key in {"mesh-audit", "reference-field-export"}
            else stage
            for stage in self._stages
        )

    @staticmethod
    def _inventory(plan: AttemptPlan, stages: tuple[WorkflowStage, ...]) -> bytes:
        value = {
            "workflow_key": plan.workflow_key,
            "run_id": plan.run_id,
            "attempt_number": plan.attempt_number,
            "case_digest": sha256(
                json.dumps(plan.case_card, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
            "declared_inputs": sorted(plan.declared_inputs),
            "stages": [asdict(stage) for stage in stages],
        }
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

    @staticmethod
    def _valid_graph(stages: tuple[WorkflowStage, ...]) -> bool:
        seen: set[str] = set()
        for stage in stages:
            if not stage.key or stage.key in seen or set(stage.depends_on) - seen:
                return False
            if stage.execution_kind == "collector" and (
                stage.adapter_service or not stage.collector_profile
            ):
                return False
            if stage.execution_kind == "workload" and (
                not stage.adapter_service or stage.collector_profile
            ):
                return False
            if (
                stage.image != SOLVER_IMAGE
                or stage.failure_policy != "stop"
                or stage.resource_class != "cpu"
            ):
                return False
            seen.add(stage.key)
        return True


class HeraWorkflowRenderer:
    """Render YAML-compatible Argo data and round-trip its complete stage inventory."""

    def render_and_validate(self, workflow: CompiledWorkflow) -> RenderedWorkflow:
        if sha256(workflow.canonical_inventory).hexdigest() != workflow.inventory_digest:
            raise ValueError("Canonical inventory digest mismatch.")
        templates: list[dict[str, Any]] = [
            {
                "name": "cmc-workflow",
                "dag": {
                    "tasks": [
                        {"name": stage.key, "dependencies": list(stage.depends_on)}
                        for stage in workflow.stages
                    ]
                },
            }
        ]
        for stage in workflow.stages:
            templates.append(
                {
                    "name": stage.key,
                    "container": {
                        "image": stage.image,
                        "command": list(stage.command),
                        "volumeMounts": [{"mountPath": mount} for mount in stage.mounts],
                    },
                    "metadata": {
                        "annotations": {
                            "cmc.workflow/stage": json.dumps(
                                asdict(stage), sort_keys=True, separators=(",", ":")
                            )
                        }
                    },
                    "retryStrategy": {"limit": "0"},
                    "nodeSelector": {"cmc.resource": stage.resource_class},
                }
            )
        document = {
            "apiVersion": "argoproj.io/v1alpha1",
            "kind": "Workflow",
            "metadata": {
                "labels": {
                    "cmc.workflow/key": workflow.workflow_key,
                    "cmc.workflow/inventory-digest": workflow.inventory_digest,
                },
                "annotations": {"cmc.workflow/inventory": workflow.canonical_inventory.decode()},
            },
            "spec": {
                "entrypoint": "cmc-workflow",
                "volumes": [{"name": "artifacts", "emptyDir": {}}],
                "templates": templates,
            },
        }
        rendered = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        self.validate_rendered(workflow, document)
        return RenderedWorkflow(document, rendered, workflow.inventory_digest)

    def validate_rendered(self, workflow: CompiledWorkflow, document: dict[str, Any]) -> None:
        if (
            document.get("kind") != "Workflow"
            or document.get("apiVersion") != "argoproj.io/v1alpha1"
        ):
            raise ValueError("Rendered document is not an Argo Workflow.")
        metadata = document.get("metadata", {})
        if (
            metadata.get("annotations", {}).get("cmc.workflow/inventory")
            != workflow.canonical_inventory.decode()
        ):
            raise ValueError("Rendered workflow inventory mismatch.")
        templates = document.get("spec", {}).get("templates", [])
        task_names = (
            [task["name"] for task in templates[0].get("dag", {}).get("tasks", [])]
            if templates
            else []
        )
        stages: list[WorkflowStage] = []
        for template in templates[1:]:
            try:
                value = json.loads(template["metadata"]["annotations"]["cmc.workflow/stage"])
                for key in ("depends_on", "command", "input_roles", "output_roles", "mounts"):
                    value[key] = tuple(value[key])
                stage = WorkflowStage(**value)
            except (KeyError, TypeError, json.JSONDecodeError) as error:
                raise ValueError("Rendered workflow has no complete stage inventory.") from error
            container = template.get("container", {})
            if (
                template.get("name") != stage.key
                or container.get("image") != stage.image
                or tuple(container.get("command", ())) != stage.command
            ):
                raise ValueError("Rendered workload does not match its declared stage.")
            if tuple(m["mountPath"] for m in container.get("volumeMounts", ())) != stage.mounts:
                raise ValueError("Rendered mounts do not match declared stage.")
            stages.append(stage)
        if tuple(stages) != workflow.stages or task_names != [
            stage.key for stage in workflow.stages
        ]:
            raise ValueError("Rendered workflow is not congruent with canonical inventory.")

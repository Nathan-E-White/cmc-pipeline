"""Execute compiled plans without exposing runner selection to admitted case cards."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Protocol

from app.case_executor import ExecutionRequest, ExecutionResult
from app.run_mirror import ArtifactReceipt
from app.workflow_compiler import CompiledWorkflow, WorkflowStage


class LocalStageRunner(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...


@dataclass(frozen=True)
class StageFact:
    stage_key: str
    event_type: str
    exit_code: int | None = None
    reason: str | None = None


@dataclass(frozen=True)
class WorkflowExecutionReceipt:
    inventory_digest: str
    completed_stages: tuple[str, ...]
    facts: tuple[StageFact, ...]
    result: ExecutionResult
    artifacts: tuple[tuple[str, ArtifactReceipt], ...] = ()


@dataclass(frozen=True)
class ExecutionRefusal:
    reason: str
    facts: tuple[StageFact, ...]
    result: ExecutionResult


class WorkflowRuntime:
    """Compose-equivalent adapter; workload service and collector profile come from stages."""

    def __init__(self, runner: LocalStageRunner) -> None:
        self._runner = runner

    def execute(
        self,
        workflow: CompiledWorkflow,
        request: ExecutionRequest,
        collect: Callable[[WorkflowStage], tuple[tuple[str, ArtifactReceipt], ...]],
    ) -> WorkflowExecutionReceipt | ExecutionRefusal:
        if workflow.target != "compose":
            return ExecutionRefusal(
                "target_not_executable_locally", (), ExecutionResult(125, "", "")
            )
        completed: list[str] = []
        facts: list[StageFact] = [StageFact("workflow", "workflow-rendered")]
        result = ExecutionResult(0, "", "")
        artifacts: tuple[tuple[str, ArtifactReceipt], ...] = ()
        for stage in workflow.stages:
            facts.append(StageFact(stage.key, "stage-started"))
            if stage.execution_kind == "collector":
                try:
                    artifacts = collect(stage)
                except (TypeError, ValueError) as error:
                    facts.append(StageFact(stage.key, "stage-failed", reason=type(error).__name__))
                    return ExecutionRefusal(f"stage_failed:{stage.key}", tuple(facts), result)
                facts.append(StageFact(stage.key, "stage-finished", 0))
                completed.append(stage.key)
                continue
            stage_request = replace(
                request,
                runner_key=stage.adapter_service or "",
                command=stage.command,
                stage_key=stage.key,
                container_name=f"{request.container_name}-{stage.key}",
                output_directory=(request.output_directory / stage.key)
                if stage.key == "mesh-audit"
                else request.output_directory,
            )
            result = self._runner.execute(stage_request)
            if result.exit_code != 0:
                facts.append(StageFact(stage.key, "stage-failed", result.exit_code))
                return ExecutionRefusal(f"stage_failed:{stage.key}", tuple(facts), result)
            facts.append(StageFact(stage.key, "stage-finished", result.exit_code))
            completed.append(stage.key)
        return WorkflowExecutionReceipt(
            workflow.inventory_digest, tuple(completed), tuple(facts), result, artifacts
        )

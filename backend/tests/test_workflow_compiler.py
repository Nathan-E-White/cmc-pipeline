from app.workflow_compiler import (
    AttemptPlan,
    HeraWorkflowRenderer,
    WorkflowCompiler,
    WorkflowRefusal,
)


def test_compiler_materializes_the_declared_reference_export_in_a_stable_order() -> None:
    plan = AttemptPlan(
        run_id="run-1",
        attempt_number=1,
        case_card={"case_id": "r0-elastic-displacement-e200-v1"},
        workflow_key="r0-reference-field-export/v1",
        target="compose",
        declared_inputs=("declared-case-card",),
    )

    compiled = WorkflowCompiler().compile(plan)

    assert not isinstance(compiled, WorkflowRefusal)
    assert [stage.key for stage in compiled.stages] == [
        "mesh-audit",
        "reference-field-export",
        "collect-reference-field",
    ]
    assert compiled.stages[1].image.endswith(
        "@sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8"
    )
    assert compiled.inventory_digest == WorkflowCompiler().compile(plan).inventory_digest


def test_compiler_refuses_an_undeclared_or_mutable_workflow_request() -> None:
    compiler = WorkflowCompiler()
    unknown = compiler.compile(
        AttemptPlan(
            "run-1",
            1,
            {"case_id": "r0-elastic-displacement-e200-v1"},
            "not-a-workflow",
            "compose",
            declared_inputs=("declared-case-card",),
        )
    )
    mutable = compiler.compile(
        AttemptPlan(
            "run-1",
            1,
            {"case_id": "r0-elastic-displacement-e200-v1"},
            "r0-reference-field-export/v1",
            "compose",
            declared_inputs=("declared-case-card",),
            image_overrides={"reference-field-export": "cmc/reference:latest"},
        )
    )

    assert unknown == WorkflowRefusal("unknown_workflow", "not-a-workflow")
    assert mutable == WorkflowRefusal("mutable_execution_request", "r0-reference-field-export/v1")


def test_hera_renderer_validates_the_same_canonical_inventory_as_compose() -> None:
    compiled = WorkflowCompiler().compile(
        AttemptPlan(
            "run-1",
            1,
            {"case_id": "r0-elastic-displacement-e200-v1"},
            "r0-reference-field-export/v1",
            "compose",
            declared_inputs=("declared-case-card",),
        )
    )
    assert not isinstance(compiled, WorkflowRefusal)

    rendered = HeraWorkflowRenderer().render_and_validate(compiled)

    assert rendered.inventory_digest == compiled.inventory_digest
    assert rendered.document["kind"] == "Workflow"
    assert [template["name"] for template in rendered.document["spec"]["templates"][1:]] == [
        "mesh-audit",
        "reference-field-export",
        "collect-reference-field",
    ]


def test_compiler_binds_attempt_identity_and_renderer_detects_mutated_stage() -> None:
    compiler = WorkflowCompiler()
    first = compiler.compile(
        AttemptPlan(
            "run-1",
            1,
            {"case_id": "r0-elastic-displacement-e200-v1"},
            "r0-reference-field-export/v1",
            "compose",
            declared_inputs=("declared-case-card",),
        )
    )
    second = compiler.compile(
        AttemptPlan(
            "run-2",
            1,
            {"case_id": "r0-elastic-displacement-e200-v1"},
            "r0-reference-field-export/v1",
            "compose",
            declared_inputs=("declared-case-card",),
        )
    )
    assert not isinstance(first, WorkflowRefusal) and not isinstance(second, WorkflowRefusal)
    assert first.inventory_digest != second.inventory_digest
    renderer = HeraWorkflowRenderer()
    rendered = renderer.render_and_validate(first)
    rendered.document["spec"]["templates"][1]["container"]["command"] = ["tampered"]
    import pytest

    with pytest.raises(ValueError, match="does not match"):
        renderer.validate_rendered(first, rendered.document)


def test_compose_and_hera_share_the_target_neutral_inventory() -> None:
    compiler = WorkflowCompiler()
    compose = compiler.compile(
        AttemptPlan(
            "run-1",
            1,
            {"case_id": "r0-elastic-displacement-e200-v1"},
            "r0-reference-field-export/v1",
            "compose",
            declared_inputs=("declared-case-card",),
        )
    )
    hera = compiler.compile(
        AttemptPlan(
            "run-1",
            1,
            {"case_id": "r0-elastic-displacement-e200-v1"},
            "r0-reference-field-export/v1",
            "hera",
            declared_inputs=("declared-case-card",),
        )
    )
    assert not isinstance(compose, WorkflowRefusal) and not isinstance(hera, WorkflowRefusal)
    assert compose.inventory_digest == hera.inventory_digest

"""Public-seam tests for browser-safe physics result projections."""

from app.physics_result_view import PhysicsResultView


class DeclaredFieldArtifacts:
    def __init__(self, response: dict) -> None:
        self.response = response

    def field_artifact(self, run_id: str) -> dict:
        assert run_id == "run-1"
        return self.response


def test_exposes_accepted_reference_field_without_manufacturing_an_onnx_result() -> None:
    view = PhysicsResultView(
        DeclaredFieldArtifacts(
            {"state": "available", "payload": {"provenance": {"run_id": "run-1"}}}
        )
    ).result("run-1")

    assert view["reference_result"] == {"state": "available", "kind": "accepted_field_artifact"}
    assert view["accepted_reference_field"]["state"] == "available"
    assert view["experimental_onnx_observation"]["state"] == "unavailable"
    assert view["experimental_onnx_observation"]["reason"] == "no_declared_compatible_release"


def test_keeps_an_indeterminate_field_explicitly_indeterminate() -> None:
    view = PhysicsResultView(
        DeclaredFieldArtifacts(
            {"state": "indeterminate", "reason": "run_not_accepted", "provenance": {"run_id": "run-1"}}
        )
    ).result("run-1")

    assert view["reference_result"]["state"] == "indeterminate"
    assert view["field_availability"] == {"state": "indeterminate", "reason": "run_not_accepted"}
    assert view["accepted_reference_field"] is None

"""Browser-safe physics-result projection; it does not expose solver artifacts."""

from __future__ import annotations

from typing import Any, Protocol


class FieldArtifactReader(Protocol):
    def field_artifact(self, run_id: str) -> dict[str, Any]: ...


class PhysicsResultView:
    """A small read-side seam for one run's reference and experimental observations."""

    def __init__(self, field_artifacts: FieldArtifactReader) -> None:
        self._field_artifacts = field_artifacts

    def result(self, run_id: str) -> dict[str, Any]:
        artifact = self._field_artifacts.field_artifact(run_id)
        state = artifact["state"]
        provenance = artifact.get("payload", {}).get("provenance") or artifact.get("provenance", {})
        return {
            "version": "cmc.physics-result-view.v1",
            "run_id": run_id,
            "reference_result": {
                "state": "available" if state == "available" else state,
                "kind": "accepted_field_artifact" if state == "available" else "unavailable",
            },
            "field_availability": {"state": state, "reason": artifact.get("reason")},
            "provenance": provenance,
            "accepted_reference_field": artifact if state == "available" else None,
            "experimental_onnx_observation": {
                "state": "unavailable",
                "reason": "no_declared_compatible_release",
                "claim_boundary": "Experimental only; cannot alter reference lifecycle, outcome, acceptance, or field availability.",
            },
        }

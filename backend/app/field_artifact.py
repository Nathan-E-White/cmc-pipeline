"""Translate one accepted XDMF/HDF5 field set into a browser-safe payload."""

from __future__ import annotations

from typing import Any, Protocol

from app.field_set import DeclaredFieldSet, FieldSetError
from app.run_mirror import ArtifactIntegrityError, ArtifactReceipt, RunSnapshot


class FieldArtifactSource(Protocol):
    def inspect(self, run_id: str) -> RunSnapshot: ...

    def artifacts(self, run_id: str) -> dict[str, ArtifactReceipt]: ...

    def get_bytes(self, artifact: ArtifactReceipt) -> bytes: ...


class FieldArtifact:
    """The Field Artifact interface; parsing and object-store details stay inside it."""

    def __init__(self, source: FieldArtifactSource) -> None:
        self._source = source

    def field_artifact(self, run_id: str) -> dict[str, Any]:
        snapshot = self._source.inspect(run_id)
        provenance = self._provenance(snapshot)
        if (snapshot.lifecycle, snapshot.outcome, snapshot.evidence_disposition) != (
            "terminal",
            "solved",
            "accepted",
        ):
            return {
                "version": "cmc.field-artifact.v1",
                "state": "indeterminate",
                "reason": "run_not_accepted",
                "provenance": provenance,
            }
        try:
            artifacts = self._source.artifacts(run_id)
            field_set = DeclaredFieldSet.resolve(artifacts, self._source.get_bytes)
            payload = field_set.browser_payload()
        except ArtifactIntegrityError:
            return self._unavailable("digest_mismatch", provenance)
        except FieldSetError as error:
            return self._unavailable(error.reason, provenance)
        return {
            "version": "cmc.field-artifact.v1",
            "state": "available",
            "payload": {
                **payload,
                "provenance": {
                    **provenance,
                    "claim_boundary": field_set.claim_boundary,
                    "artifact_digests": field_set.artifact_digests,
                },
            },
        }

    @staticmethod
    def _provenance(snapshot: RunSnapshot) -> dict[str, Any]:
        return {
            "run_id": snapshot.run_id,
            "case_digest": snapshot.case_digest,
            "outcome": snapshot.outcome,
            "evidence_disposition": snapshot.evidence_disposition,
        }

    @staticmethod
    def _unavailable(reason: str, provenance: dict[str, Any]) -> dict[str, Any]:
        return {
            "version": "cmc.field-artifact.v1",
            "state": "unavailable",
            "reason": reason,
            "provenance": provenance,
        }

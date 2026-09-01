"""Public-seam tests for the V3 Field Artifact module."""

from __future__ import annotations

import json
from hashlib import sha256

import h5py
import numpy as np

from app.field_artifact import FieldArtifact
from app.run_mirror import ArtifactIntegrityError, ArtifactReceipt, RunSnapshot


def receipt(content: bytes, media_type: str) -> ArtifactReceipt:
    digest = sha256(content).hexdigest()
    return ArtifactReceipt(digest, len(content), media_type, f"sha256/{digest}")


class MemoryArtifacts:
    def __init__(
        self, snapshot: RunSnapshot, records: dict[str, tuple[ArtifactReceipt, bytes]]
    ) -> None:
        self.snapshot = snapshot
        self.records = records

    def inspect(self, run_id: str) -> RunSnapshot:
        assert run_id == self.snapshot.run_id
        return self.snapshot

    def artifacts(self, run_id: str) -> dict[str, ArtifactReceipt]:
        assert run_id == self.snapshot.run_id
        return {role: value[0] for role, value in self.records.items()}

    def get_bytes(self, artifact: ArtifactReceipt) -> bytes:
        for known, content in self.records.values():
            if known.sha256 == artifact.sha256:
                if sha256(content).hexdigest() != artifact.sha256:
                    raise ArtifactIntegrityError(
                        "Stored artifact does not match its declared SHA-256 identity."
                    )
                return content
        raise AssertionError("unknown artifact")


def accepted_snapshot() -> RunSnapshot:
    return RunSnapshot("run-1", "case-digest", "terminal", "solved", 1, "accepted")


def xdmf() -> bytes:
    return b"""<?xml version="1.0"?>
<Xdmf Version="3.0"><Domain><Grid Name="mesh" GridType="Uniform">
<Topology TopologyType="Triangle" NumberOfElements="1"><DataItem Dimensions="1 3" Format="HDF">field.h5:/mesh/cells</DataItem></Topology>
<Geometry GeometryType="XY"><DataItem Dimensions="3 2" Format="HDF">field.h5:/mesh/points</DataItem></Geometry>
<Attribute Name="displacement_mm" AttributeType="Vector" Center="Node"><DataItem Dimensions="3 2" Format="HDF">field.h5:/fields/displacement</DataItem></Attribute>
</Grid></Domain></Xdmf>"""


def hdf5_bytes(tmp_path) -> bytes:
    path = tmp_path / "field.h5"
    with h5py.File(path, "w") as file:
        file["mesh/cells"] = np.array([[0, 1, 2]], dtype=np.int64)
        file["mesh/points"] = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
        file["fields/displacement"] = np.array([[0.0, 0.0], [0.1, 0.0], [0.0, 0.2]])
    return path.read_bytes()


def manifest(*, units: str = "mm", hdf5_role: str = "field/displacement/hdf5") -> bytes:
    return json.dumps(
        {
            "version": "cmc.field-set-manifest.v1",
            "field": {
                "id": "displacement",
                "name": "displacement_mm",
                "units": units,
                "association": "node",
                "components": 2,
                "xdmf_role": "field/displacement/xdmf",
                "hdf5_role": hdf5_role,
            },
            "claim_boundary": "Local reference evidence; not physical validation.",
            "acceptance_role": "field/displacement/acceptance",
        }
    ).encode()


def records(
    tmp_path, *, manifest_bytes: bytes | None = None
) -> dict[str, tuple[ArtifactReceipt, bytes]]:
    manifest_bytes = manifest_bytes or manifest()
    values = {
        "field-set-manifest": (manifest_bytes, "application/vnd.cmc.field-set-manifest+json"),
        "field/displacement/xdmf": (xdmf(), "application/x-xdmf+xml"),
        "field/displacement/hdf5": (hdf5_bytes(tmp_path), "application/x-hdf5"),
        "field/displacement/acceptance": (
            json.dumps(
                {
                    "version": "cmc.r0-field-acceptance.v1",
                    "status": "accepted",
                    "gates": {"mesh_audit": "accepted", "solution": "solved"},
                }
            ).encode(),
            "application/vnd.cmc.r0-field-acceptance+json",
        ),
    }
    return {
        role: (receipt(content, media_type), content)
        for role, (content, media_type) in values.items()
    }


def test_field_artifact_projects_an_accepted_triangular_displacement_field(tmp_path) -> None:
    response = FieldArtifact(
        MemoryArtifacts(accepted_snapshot(), records(tmp_path))
    ).field_artifact("run-1")

    assert response["state"] == "available"
    assert response["version"] == "cmc.field-artifact.v1"
    assert response["payload"]["geometry"] == {
        "positions": [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
        "triangles": [[0, 1, 2]],
    }
    assert response["payload"]["field"] == {
        "id": "displacement",
        "name": "displacement_mm",
        "units": "mm",
        "association": "node",
        "components": 2,
        "values": [[0.0, 0.0], [0.1, 0.0], [0.0, 0.2]],
    }
    assert response["payload"]["provenance"]["case_digest"] == "case-digest"
    assert response["payload"]["provenance"]["artifact_digests"]["field-set-manifest"]


def test_field_artifact_returns_indeterminate_for_a_non_accepted_run(tmp_path) -> None:
    snapshot = RunSnapshot("run-1", "case-digest", "terminal", "indeterminate", 1, "indeterminate")
    response = FieldArtifact(MemoryArtifacts(snapshot, records(tmp_path))).field_artifact("run-1")

    assert response == {
        "version": "cmc.field-artifact.v1",
        "state": "indeterminate",
        "reason": "run_not_accepted",
        "provenance": {
            "run_id": "run-1",
            "case_digest": "case-digest",
            "outcome": "indeterminate",
            "evidence_disposition": "indeterminate",
        },
    }


def test_field_artifact_returns_unavailable_when_the_hdf5_companion_is_missing(tmp_path) -> None:
    source = records(tmp_path)
    source.pop("field/displacement/hdf5")
    response = FieldArtifact(MemoryArtifacts(accepted_snapshot(), source)).field_artifact("run-1")

    assert response["state"] == "unavailable"
    assert response["reason"] == "missing_artifact"


def test_field_artifact_returns_unavailable_when_units_are_undeclared(tmp_path) -> None:
    response = FieldArtifact(
        MemoryArtifacts(accepted_snapshot(), records(tmp_path, manifest_bytes=manifest(units="")))
    ).field_artifact("run-1")

    assert response["state"] == "unavailable"
    assert response["reason"] == "invalid_manifest"


def test_field_artifact_rejects_a_field_set_with_the_wrong_declared_media_type(tmp_path) -> None:
    source = records(tmp_path)
    receipt_value, content = source["field-set-manifest"]
    source["field-set-manifest"] = (
        ArtifactReceipt(
            receipt_value.sha256,
            receipt_value.byte_length,
            "text/plain",
            receipt_value.storage_key,
        ),
        content,
    )
    response = FieldArtifact(MemoryArtifacts(accepted_snapshot(), source)).field_artifact("run-1")

    assert response["state"] == "unavailable"
    assert response["reason"] == "invalid_manifest"


def test_field_artifact_rejects_digest_mismatch(tmp_path) -> None:
    source = records(tmp_path)
    receipt_value, _content = source["field/displacement/hdf5"]
    source["field/displacement/hdf5"] = (receipt_value, b"tampered")
    response = FieldArtifact(MemoryArtifacts(accepted_snapshot(), source)).field_artifact("run-1")
    assert response["reason"] == "digest_mismatch"


def test_field_artifact_rejects_malformed_connectivity(tmp_path) -> None:
    path = tmp_path / "broken.h5"
    with h5py.File(path, "w") as file:
        file["mesh/cells"] = np.array([[0, 1, 9]], dtype=np.int64)
        file["mesh/points"] = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
        file["fields/displacement"] = np.array([[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]])
    source = records(tmp_path)
    source["field/displacement/hdf5"] = (
        receipt(path.read_bytes(), "application/x-hdf5"),
        path.read_bytes(),
    )
    response = FieldArtifact(MemoryArtifacts(accepted_snapshot(), source)).field_artifact("run-1")
    assert response["reason"] == "invalid_geometry"


def test_field_artifact_rejects_field_cardinality_mismatch(tmp_path) -> None:
    path = tmp_path / "short.h5"
    with h5py.File(path, "w") as file:
        file["mesh/cells"] = np.array([[0, 1, 2]], dtype=np.int64)
        file["mesh/points"] = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
        file["fields/displacement"] = np.array([[0.0, 0.0], [0.0, 0.0]])
    source = records(tmp_path)
    source["field/displacement/hdf5"] = (
        receipt(path.read_bytes(), "application/x-hdf5"),
        path.read_bytes(),
    )
    response = FieldArtifact(MemoryArtifacts(accepted_snapshot(), source)).field_artifact("run-1")
    assert response["reason"] == "field_cardinality_mismatch"


def test_field_artifact_rejects_unsupported_topology(tmp_path) -> None:
    source = records(tmp_path)
    content = xdmf().replace(b'TopologyType="Triangle"', b'TopologyType="Quadrilateral"')
    source["field/displacement/xdmf"] = (receipt(content, "application/x-xdmf+xml"), content)
    response = FieldArtifact(MemoryArtifacts(accepted_snapshot(), source)).field_artifact("run-1")
    assert response["reason"] == "unsupported_topology"

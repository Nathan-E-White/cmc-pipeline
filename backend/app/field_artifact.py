"""Translate one accepted XDMF/HDF5 field set into a browser-safe payload."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any, Protocol
from xml.etree import ElementTree

import h5py
import numpy as np

from app.run_mirror import ArtifactIntegrityError, ArtifactReceipt, RunSnapshot


class FieldArtifactSource(Protocol):
    def inspect(self, run_id: str) -> RunSnapshot: ...

    def artifacts(self, run_id: str) -> dict[str, ArtifactReceipt]: ...

    def get_bytes(self, artifact: ArtifactReceipt) -> bytes: ...


class FieldArtifactFailure(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


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
            manifest = self._manifest(self._required_bytes(artifacts, "field-set-manifest"))
            field = manifest["field"]
            self._acceptance(self._required_bytes(artifacts, manifest["acceptance_role"]))
            xdmf = self._required_bytes(artifacts, field["xdmf_role"])
            hdf5 = self._required_bytes(artifacts, field["hdf5_role"])
            payload = self._payload(xdmf, hdf5, field)
        except ArtifactIntegrityError:
            return self._unavailable("digest_mismatch", provenance)
        except FieldArtifactFailure as error:
            return self._unavailable(error.reason, provenance)
        return {
            "version": "cmc.field-artifact.v1",
            "state": "available",
            "payload": {
                **payload,
                "provenance": {
                    **provenance,
                    "claim_boundary": manifest["claim_boundary"],
                    "artifact_digests": {
                        role: receipt.sha256 for role, receipt in artifacts.items()
                    },
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

    def _required_bytes(self, artifacts: dict[str, ArtifactReceipt], role: str) -> bytes:
        artifact = artifacts.get(role)
        if artifact is None:
            raise FieldArtifactFailure("missing_artifact")
        return self._source.get_bytes(artifact)

    @staticmethod
    def _manifest(content: bytes) -> dict[str, Any]:
        try:
            value = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FieldArtifactFailure("invalid_manifest") from error
        if not isinstance(value, dict) or value.get("version") != "cmc.field-set-manifest.v1":
            raise FieldArtifactFailure("invalid_manifest")
        field = value.get("field")
        if not isinstance(field, dict):
            raise FieldArtifactFailure("invalid_manifest")
        required_strings = ("id", "name", "units", "association", "xdmf_role", "hdf5_role")
        if any(not isinstance(field.get(key), str) or not field[key] for key in required_strings):
            raise FieldArtifactFailure("invalid_manifest")
        if field.get("association") != "node" or field.get("components") not in {2, 3}:
            raise FieldArtifactFailure("unsupported_field")
        if not isinstance(value.get("claim_boundary"), str) or not value["claim_boundary"]:
            raise FieldArtifactFailure("invalid_manifest")
        if not isinstance(value.get("acceptance_role"), str) or not value["acceptance_role"]:
            raise FieldArtifactFailure("invalid_manifest")
        return value

    @staticmethod
    def _acceptance(content: bytes) -> None:
        try:
            value = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FieldArtifactFailure("invalid_acceptance") from error
        if not isinstance(value, dict) or value.get("version") != "cmc.r0-field-acceptance.v1":
            raise FieldArtifactFailure("invalid_acceptance")
        if value.get("status") != "accepted" or value.get("gates") != {
            "mesh_audit": "accepted",
            "solution": "solved",
        }:
            raise FieldArtifactFailure("field_not_accepted")

    @staticmethod
    def _payload(xdmf_bytes: bytes, hdf5_bytes: bytes, field: dict[str, Any]) -> dict[str, Any]:
        try:
            root = ElementTree.fromstring(xdmf_bytes)
        except ElementTree.ParseError as error:
            raise FieldArtifactFailure("invalid_xdmf") from error
        topology = FieldArtifact._one(root, "Topology")
        geometry = FieldArtifact._one(root, "Geometry")
        attributes = [node for node in root.iter() if FieldArtifact._local(node.tag) == "Attribute"]
        attribute = next((node for node in attributes if node.get("Name") == field["name"]), None)
        if attribute is None:
            raise FieldArtifactFailure("invalid_xdmf")
        if (
            topology.get("TopologyType") not in {"Triangle", "Triangle_6"}
            or geometry.get("GeometryType") != "XY"
        ):
            raise FieldArtifactFailure("unsupported_topology")
        if attribute.get("Center") != "Node" or attribute.get("AttributeType") != "Vector":
            raise FieldArtifactFailure("unsupported_field")
        cells_path = FieldArtifact._hdf_path(topology)
        points_path = FieldArtifact._hdf_path(geometry)
        values_path = FieldArtifact._hdf_path(attribute)
        try:
            with h5py.File(BytesIO(hdf5_bytes), "r") as hdf:
                cells = np.asarray(hdf[cells_path])
                points = np.asarray(hdf[points_path])
                values = np.asarray(hdf[values_path])
        except (OSError, KeyError, ValueError) as error:
            raise FieldArtifactFailure("invalid_hdf5") from error
        if (
            cells.ndim != 2
            or cells.shape[1] not in {3, 6}
            or points.ndim != 2
            or points.shape[1] != 2
        ):
            raise FieldArtifactFailure("invalid_geometry")
        if values.ndim != 2 or values.shape != (points.shape[0], field["components"]):
            raise FieldArtifactFailure("field_cardinality_mismatch")
        if not np.isfinite(points).all() or not np.isfinite(values).all():
            raise FieldArtifactFailure("invalid_field")
        if (
            not np.issubdtype(cells.dtype, np.integer)
            or (cells < 0).any()
            or (cells >= len(points)).any()
        ):
            raise FieldArtifactFailure("invalid_geometry")
        return {
            "geometry": {
                "positions": points.astype(float).tolist(),
                "triangles": cells[:, :3].astype(int).tolist(),
            },
            "field": {
                "id": field["id"],
                "name": field["name"],
                "units": field["units"],
                "association": field["association"],
                "components": field["components"],
                "values": values.astype(float).tolist(),
            },
        }

    @staticmethod
    def _one(root: ElementTree.Element, name: str) -> ElementTree.Element:
        matches = [node for node in root.iter() if FieldArtifact._local(node.tag) == name]
        if len(matches) != 1:
            raise FieldArtifactFailure("invalid_xdmf")
        return matches[0]

    @staticmethod
    def _hdf_path(node: ElementTree.Element) -> str:
        items = [child for child in node if FieldArtifact._local(child.tag) == "DataItem"]
        if len(items) != 1 or items[0].get("Format") != "HDF" or not items[0].text:
            raise FieldArtifactFailure("invalid_xdmf")
        source, separator, path = items[0].text.strip().partition(":")
        if separator != ":" or not source.endswith(".h5") or not path.startswith("/"):
            raise FieldArtifactFailure("invalid_xdmf")
        return path

    @staticmethod
    def _local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

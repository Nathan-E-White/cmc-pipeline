"""Resolve a declared field set without leaking its artifact roles to callers."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol
from xml.etree import ElementTree

import h5py
import numpy as np


class ArtifactIdentity(Protocol):
    sha256: str
    media_type: str


@dataclass(frozen=True)
class LocalArtifact:
    path: str
    sha256: str
    media_type: str


class FieldSetError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class AcceptancePolicy:
    version: str
    gates: dict[str, str]


ACCEPTANCE_POLICIES = {
    "cmc.r0-field-acceptance.v1": AcceptancePolicy(
        "cmc.r0-field-acceptance.v1", {"mesh_audit": "accepted", "solution": "solved"}
    )
}


@dataclass(frozen=True)
class DeclaredFieldSet:
    """One accepted declared field, resolved from content-addressed artifacts."""

    field: dict[str, Any]
    xdmf: bytes
    hdf5: bytes
    claim_boundary: str
    artifact_digests: dict[str, str]

    @classmethod
    def resolve(
        cls,
        artifacts: dict[str, ArtifactIdentity],
        get_bytes: Callable[[ArtifactIdentity], bytes],
    ) -> DeclaredFieldSet:
        manifest = cls._manifest(
            cls._required_bytes(
                artifacts,
                "field-set-manifest",
                "application/vnd.cmc.field-set-manifest+json",
                get_bytes,
            )
        )
        field = manifest["field"]
        cls._acceptance(
            cls._required_bytes(
                artifacts,
                manifest["acceptance_role"],
                "application/vnd.cmc.r0-field-acceptance+json",
                get_bytes,
            )
        )
        if "pair_map_role" in manifest:
            cls._pair_map(
                cls._required_bytes(
                    artifacts,
                    manifest["pair_map_role"],
                    "application/vnd.cmc.opened-crack-pairs+json",
                    get_bytes,
                )
            )
        return cls(
            field=field,
            xdmf=cls._required_bytes(
                artifacts, field["xdmf_role"], "application/x-xdmf+xml", get_bytes
            ),
            hdf5=cls._required_bytes(
                artifacts, field["hdf5_role"], "application/x-hdf5", get_bytes
            ),
            claim_boundary=manifest["claim_boundary"],
            artifact_digests={
                role: artifacts[role].sha256 for role in cls.required_roles(manifest)
            },
        )

    @classmethod
    def validate_declared_files(cls, files: dict[str, tuple[str, str]]) -> None:
        """Validate a runner's local Field Set evidence before it becomes accepted."""
        manifest = files.get("field-set-manifest")
        if manifest is None or manifest[1] != "application/vnd.cmc.field-set-manifest+json":
            raise FieldSetError("missing_artifact")
        try:
            with open(manifest[0], "rb") as stream:
                value = cls._manifest(stream.read())
            required = cls.required_roles(value)
            if not required.issubset(files):
                raise FieldSetError("missing_artifact")
            field = value["field"]
            if files[field["xdmf_role"]][1] != "application/x-xdmf+xml":
                raise FieldSetError("invalid_manifest")
            if files[field["hdf5_role"]][1] != "application/x-hdf5":
                raise FieldSetError("invalid_manifest")
            acceptance = files[value["acceptance_role"]]
            if acceptance[1] != "application/vnd.cmc.r0-field-acceptance+json":
                raise FieldSetError("invalid_acceptance")
            with open(acceptance[0], "rb") as stream:
                cls._acceptance(stream.read())
            pair_role = value.get("pair_map_role")
            if pair_role is not None:
                if (
                    not isinstance(pair_role, str)
                    or files.get(pair_role, ("", ""))[1]
                    != "application/vnd.cmc.opened-crack-pairs+json"
                ):
                    raise FieldSetError("missing_paired_lip_evidence")
                with open(files[pair_role][0], "rb") as stream:
                    cls._pair_map(stream.read())
            local_artifacts = {
                role: LocalArtifact(path, "local", media_type)
                for role, (path, media_type) in files.items()
            }
            cls.resolve(
                local_artifacts,
                lambda artifact: Path(artifact.path).read_bytes(),
            ).browser_payload()
        except OSError as error:
            raise FieldSetError("missing_artifact") from error

    @staticmethod
    def required_roles(manifest: dict[str, Any]) -> frozenset[str]:
        field = manifest["field"]
        return frozenset(
            {
                "field-set-manifest",
                field["xdmf_role"],
                field["hdf5_role"],
                manifest["acceptance_role"],
                *([manifest["pair_map_role"]] if "pair_map_role" in manifest else []),
            }
        )

    @staticmethod
    def _required_bytes(
        artifacts: dict[str, ArtifactIdentity],
        role: str,
        media_type: str,
        get_bytes: Callable[[ArtifactIdentity], bytes],
    ) -> bytes:
        artifact = artifacts.get(role)
        if artifact is None:
            raise FieldSetError("missing_artifact")
        if artifact.media_type != media_type:
            raise FieldSetError("invalid_manifest")
        return get_bytes(artifact)

    @staticmethod
    def _manifest(content: bytes) -> dict[str, Any]:
        try:
            value = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FieldSetError("invalid_manifest") from error
        if not isinstance(value, dict) or value.get("version") != "cmc.field-set-manifest.v1":
            raise FieldSetError("invalid_manifest")
        field = value.get("field")
        if not isinstance(field, dict):
            raise FieldSetError("invalid_manifest")
        required = ("id", "name", "units", "association", "xdmf_role", "hdf5_role")
        if any(not isinstance(field.get(key), str) or not field[key] for key in required):
            raise FieldSetError("invalid_manifest")
        if field.get("association") != "node" or field.get("components") not in {2, 3}:
            raise FieldSetError("unsupported_field")
        if not isinstance(value.get("claim_boundary"), str) or not value["claim_boundary"]:
            raise FieldSetError("invalid_manifest")
        if not isinstance(value.get("acceptance_role"), str) or not value["acceptance_role"]:
            raise FieldSetError("invalid_manifest")
        if "pair_map_role" in value and (
            not isinstance(value["pair_map_role"], str) or not value["pair_map_role"]
        ):
            raise FieldSetError("invalid_manifest")
        return value

    @staticmethod
    def _acceptance(content: bytes) -> None:
        try:
            value = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FieldSetError("invalid_acceptance") from error
        if not isinstance(value, dict):
            raise FieldSetError("invalid_acceptance")
        policy = ACCEPTANCE_POLICIES.get(value.get("version"))
        if policy is None:
            raise FieldSetError("invalid_acceptance")
        if value.get("status") != "accepted" or value.get("gates") != policy.gates:
            raise FieldSetError("field_not_accepted")

    @staticmethod
    def _pair_map(content: bytes) -> None:
        try:
            value = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise FieldSetError("invalid_paired_lip_evidence") from error
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("ordered_element_pairs"), list)
            or not value["ordered_element_pairs"]
        ):
            raise FieldSetError("invalid_paired_lip_evidence")

    def browser_payload(self) -> dict[str, Any]:
        """Project the declared supported field without revealing raw artifact paths."""
        try:
            root = ElementTree.fromstring(self.xdmf)
        except ElementTree.ParseError as error:
            raise FieldSetError("invalid_xdmf") from error
        topology = self._one(root, "Topology")
        geometry = self._one(root, "Geometry")
        attributes = [node for node in root.iter() if self._local(node.tag) == "Attribute"]
        attribute = next(
            (node for node in attributes if node.get("Name") == self.field["name"]), None
        )
        if attribute is None:
            raise FieldSetError("invalid_xdmf")
        if (
            topology.get("TopologyType") not in {"Triangle", "Triangle_6"}
            or geometry.get("GeometryType") != "XY"
        ):
            raise FieldSetError("unsupported_topology")
        if attribute.get("Center") != "Node" or attribute.get("AttributeType") != "Vector":
            raise FieldSetError("unsupported_field")
        try:
            with h5py.File(BytesIO(self.hdf5), "r") as hdf:
                cells = np.asarray(hdf[self._hdf_path(topology)])
                points = np.asarray(hdf[self._hdf_path(geometry)])
                values = np.asarray(hdf[self._hdf_path(attribute)])
        except (OSError, KeyError, ValueError) as error:
            raise FieldSetError("invalid_hdf5") from error
        if (
            cells.ndim != 2
            or cells.shape[1] not in {3, 6}
            or points.ndim != 2
            or points.shape[1] != 2
        ):
            raise FieldSetError("invalid_geometry")
        if values.ndim != 2 or values.shape != (points.shape[0], self.field["components"]):
            raise FieldSetError("field_cardinality_mismatch")
        if not np.isfinite(points).all() or not np.isfinite(values).all():
            raise FieldSetError("invalid_field")
        if (
            not np.issubdtype(cells.dtype, np.integer)
            or (cells < 0).any()
            or (cells >= len(points)).any()
        ):
            raise FieldSetError("invalid_geometry")
        return {
            "geometry": {
                "positions": points.astype(float).tolist(),
                "triangles": cells[:, :3].astype(int).tolist(),
            },
            "field": {
                "id": self.field["id"],
                "name": self.field["name"],
                "units": self.field["units"],
                "association": self.field["association"],
                "components": self.field["components"],
                "values": values.astype(float).tolist(),
            },
        }

    @staticmethod
    def _one(root: ElementTree.Element, name: str) -> ElementTree.Element:
        matches = [node for node in root.iter() if DeclaredFieldSet._local(node.tag) == name]
        if len(matches) != 1:
            raise FieldSetError("invalid_xdmf")
        return matches[0]

    @staticmethod
    def _hdf_path(node: ElementTree.Element) -> str:
        items = [child for child in node if DeclaredFieldSet._local(child.tag) == "DataItem"]
        if len(items) != 1 or items[0].get("Format") != "HDF" or not items[0].text:
            raise FieldSetError("invalid_xdmf")
        source, separator, path = items[0].text.strip().partition(":")
        if separator != ":" or not source.endswith(".h5") or not path.startswith("/"):
            raise FieldSetError("invalid_xdmf")
        return path

    @staticmethod
    def _local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

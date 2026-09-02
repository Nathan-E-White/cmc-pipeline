"""Validate declared outputs before immutable artifact publication."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import ClassVar, Protocol

from app.field_set import DeclaredFieldSet, FieldSetError
from app.run_mirror import ArtifactReceipt


class ArtifactPublisher(Protocol):
    def put_bytes(self, content: bytes, media_type: str) -> ArtifactReceipt: ...


@dataclass(frozen=True)
class DeclaredOutputSet:
    profile: str
    output_root: Path
    entries: tuple[tuple[str, str, str, str | None], ...]


@dataclass(frozen=True)
class ArtifactSetReceipt:
    profile: str
    artifacts: tuple[tuple[str, ArtifactReceipt], ...]


@dataclass(frozen=True)
class PublicationRefusal:
    reason: str


class TypedArtifactCollector:
    """The only module allowed to turn scoped bytes into artifact receipts."""

    _profiles: ClassVar[dict[str, dict[str, str]]] = {
        "reference-field/v1": {},
        "reference-corpus/v1": {"corpus-receipt": "application/vnd.cmc.reference-corpus+json"},
        "model-release/v1": {
            "model-release": "application/vnd.cmc.model-release+json",
            "provenance-closure": "application/vnd.cmc.provenance-closure+json",
        },
        "surrogate-onnx/v1": {
            "surrogate-onnx": "application/onnx",
            "model-release": "application/vnd.cmc.model-release+json",
        },
        "surrogate-observation/v1": {
            "surrogate-observation": "application/vnd.cmc.surrogate-observation+json",
            "provenance-closure": "application/vnd.cmc.provenance-closure+json",
        },
    }

    def __init__(self, publisher: ArtifactPublisher) -> None:
        self._publisher = publisher

    def collect(self, outputs: DeclaredOutputSet) -> ArtifactSetReceipt | PublicationRefusal:
        required = self._profiles.get(outputs.profile)
        if required is None:
            return PublicationRefusal("unknown_profile")
        root = outputs.output_root.resolve()
        files: dict[str, tuple[str, str, bytes]] = {}
        for role, relative_path, media_type, expected_digest in outputs.entries:
            declared_role = (
                role == "field-set-manifest" or role.startswith("field/")
                if outputs.profile == "reference-field/v1"
                else role in required
            )
            if not declared_role:
                return PublicationRefusal("undeclared_role")
            if role in files:
                return PublicationRefusal("duplicate_role")
            source = (root / relative_path).resolve()
            if source != root and root not in source.parents:
                return PublicationRefusal("path_outside_output_root")
            if not source.is_file():
                return PublicationRefusal("missing_artifact")
            content = source.read_bytes()
            if expected_digest is not None and sha256(content).hexdigest() != expected_digest:
                return PublicationRefusal("digest_mismatch")
            if outputs.profile != "reference-field/v1" and media_type != required[role]:
                return PublicationRefusal("invalid_media_type")
            files[role] = (str(source), media_type, content)
        if outputs.profile == "reference-field/v1":
            try:
                DeclaredFieldSet.validate_declared_files(
                    {role: (path, media_type) for role, (path, media_type, _) in files.items()}
                )
            except FieldSetError as error:
                return PublicationRefusal(error.reason)
            try:
                manifest = json.loads(files["field-set-manifest"][2])
                if set(files) != set(DeclaredFieldSet.required_roles(manifest)):
                    return PublicationRefusal("undeclared_role")
            except KeyError, json.JSONDecodeError, TypeError:
                return PublicationRefusal("invalid_manifest")
        else:
            if set(files) != set(required):
                return PublicationRefusal("missing_required_evidence")
            if not self._valid_typed_receipt(outputs.profile, files):
                return PublicationRefusal("invalid_typed_receipt")
        if not files:
            return PublicationRefusal("missing_artifact")
        return ArtifactSetReceipt(
            outputs.profile,
            tuple(
                (role, self._publisher.put_bytes(content, media_type))
                for role, (_, media_type, content) in files.items()
            ),
        )

    @staticmethod
    def _valid_typed_receipt(profile: str, files: dict[str, tuple[str, str, bytes]]) -> bool:
        """Small schemas prevent a role token from masquerading as downstream evidence."""
        json_roles = {role for role, (_, media, _) in files.items() if media.endswith("+json")}
        try:
            values = {role: json.loads(files[role][2]) for role in json_roles}
        except UnicodeDecodeError, json.JSONDecodeError:
            return False
        if profile == "reference-corpus/v1":
            return values["corpus-receipt"].get("version") == "cmc.reference-corpus.v1" and bool(
                values["corpus-receipt"].get("members")
            )
        if profile == "model-release/v1":
            return values["model-release"].get("version") == "cmc.model-release.v1" and bool(
                values["model-release"].get("corpus_receipt_digest")
            )
        if profile == "surrogate-onnx/v1":
            return values["model-release"].get("version") == "cmc.model-release.v1"
        if profile == "surrogate-observation/v1":
            return values["surrogate-observation"].get("version") == "cmc.surrogate-observation.v1"
        return False

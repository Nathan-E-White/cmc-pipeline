"""Freeze compatible accepted reference fields into full-case splits."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from hashlib import sha256
from typing import Protocol

from app.run_mirror import ArtifactReceipt


class CorpusPublisher(Protocol):
    def put_bytes(self, content: bytes, media_type: str) -> ArtifactReceipt: ...


@dataclass(frozen=True)
class CorpusMember:
    case_id: str
    field_set_digest: str
    accepted: bool
    problem_card_digest: str
    mesh_pair_digest: str
    material_digest: str
    split: str | None = None


@dataclass(frozen=True)
class CorpusRequest:
    problem_key: str
    members: tuple[CorpusMember, ...]


@dataclass(frozen=True)
class CorpusReceipt:
    problem_key: str
    members: tuple[CorpusMember, ...]
    digest: str

    def document(self) -> bytes:
        return json.dumps(
            {
                "version": "cmc.reference-corpus.v1",
                "problem_key": self.problem_key,
                "members": [member.__dict__ for member in self.members],
                "digest": self.digest,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()


@dataclass(frozen=True)
class CorpusRefusal:
    reason: str


class CorpusCurator:
    """Own eligibility and split rules; it neither trains nor changes run outcomes."""

    def freeze(self, request: CorpusRequest) -> CorpusReceipt | CorpusRefusal:
        if request.problem_key != "r0-elastic/v1":
            return CorpusRefusal("unsupported_problem")
        if len(request.members) != 3:
            return CorpusRefusal("insufficient_independent_cases")
        case_ids = [member.case_id for member in request.members]
        field_digests = [member.field_set_digest for member in request.members]
        if len(case_ids) != len(set(case_ids)) or len(field_digests) != len(set(field_digests)):
            return CorpusRefusal("duplicate_case_membership")
        if not all(member.accepted for member in request.members):
            return CorpusRefusal("unaccepted_field_set")
        compatible = {
            (member.problem_card_digest, member.mesh_pair_digest, member.material_digest)
            for member in request.members
        }
        if len(compatible) != 1:
            return CorpusRefusal("incompatible_reference_evidence")
        if set(case_ids) != {
            "r0-elastic-displacement-e180-v1",
            "r0-elastic-displacement-e200-v1",
            "r0-elastic-displacement-e220-v1",
        }:
            return CorpusRefusal("not_declared_r0_case_family")
        ordered = sorted(request.members, key=lambda member: member.case_id)
        members = tuple(
            replace(member, split="held-out" if index == len(ordered) - 1 else "train")
            for index, member in enumerate(ordered)
        )
        identity = json.dumps(
            {
                "problem_key": request.problem_key,
                "members": [member.__dict__ for member in members],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return CorpusReceipt(request.problem_key, members, sha256(identity).hexdigest())

    def freeze_and_publish(
        self, request: CorpusRequest, publisher: CorpusPublisher
    ) -> tuple[CorpusReceipt, ArtifactReceipt] | CorpusRefusal:
        receipt = self.freeze(request)
        if isinstance(receipt, CorpusRefusal):
            return receipt
        artifact = publisher.put_bytes(
            receipt.document(), "application/vnd.cmc.reference-corpus+json"
        )
        if artifact.sha256 != sha256(receipt.document()).hexdigest():
            return CorpusRefusal("corpus_publication_integrity_failure")
        return receipt, artifact

"""Verify a compact declared artifact graph before downstream reuse."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256


@dataclass(frozen=True)
class DeclaredArtifactRoot:
    root: str
    edges: dict[str, tuple[str, ...]]
    artifact_types: dict[str, str] | None = None
    artifact_digests: dict[str, str] | None = None


@dataclass(frozen=True)
class ProvenanceClosure:
    root: str
    root_digest: str
    members: tuple[str, ...]


@dataclass(frozen=True)
class ClosureRefusal:
    reason: str


class ProvenanceClosureVerifier:
    """Check declared ancestry without becoming an artifact store or lifecycle ledger."""

    def verify(self, declared: DeclaredArtifactRoot) -> ProvenanceClosure | ClosureRefusal:
        if declared.root not in declared.edges:
            return ClosureRefusal("missing_root")
        if declared.artifact_types is None or declared.artifact_digests is None:
            return ClosureRefusal("untyped_provenance")
        if set(declared.edges) != set(declared.artifact_types) or set(declared.edges) != set(
            declared.artifact_digests
        ):
            return ClosureRefusal("incomplete_provenance")
        if any(not value or len(value) != 64 for value in declared.artifact_digests.values()):
            return ClosureRefusal("invalid_artifact_digest")
        if declared.artifact_types.get(declared.root) not in {
            "model-release",
            "surrogate-observation",
            "reference-corpus",
        }:
            return ClosureRefusal("invalid_provenance_root")
        visiting: set[str] = set()
        visited: set[str] = set()

        def walk(node: str) -> bool:
            if node in visiting:
                return False
            if node in visited:
                return True
            visiting.add(node)
            for parent in declared.edges.get(node, ()):
                if parent not in declared.edges:
                    return False
                if not walk(parent):
                    return False
            visiting.remove(node)
            visited.add(node)
            return True

        if not walk(declared.root):
            return ClosureRefusal("missing_or_cyclic_ancestor")
        digest = sha256(
            json.dumps(
                {
                    key: {
                        "parents": declared.edges[key],
                        "type": declared.artifact_types[key],
                        "digest": declared.artifact_digests[key],
                    }
                    for key in sorted(declared.edges)
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        return ProvenanceClosure(declared.root, digest, tuple(sorted(visited)))

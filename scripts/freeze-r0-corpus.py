#!/usr/bin/env python3
"""Freeze three accepted R0 Run Mirror field sets into an immutable corpus receipt."""

from __future__ import annotations

import os
import json
from hashlib import sha256
from pathlib import Path

from minio import Minio

from app.field_artifact import FieldArtifact
from app.reference_corpus import CorpusCurator, CorpusMember, CorpusRequest
from app.run_mirror import MinioDigestStore, PostgresRunMirror, canonical_case_digest
from app.v3_api import LiveFieldArtifactSource


def main() -> None:
    run_ids = os.environ["CMC_R0_CORPUS_RUN_IDS"].split(",")
    if len(run_ids) != 3:
        raise SystemExit(
            "CMC_R0_CORPUS_RUN_IDS must name exactly three accepted R0 runs."
        )
    mirror = PostgresRunMirror(os.environ["CMC_RUN_MIRROR_DSN"])
    store = MinioDigestStore(
        Minio(
            os.environ["CMC_ARTIFACT_ENDPOINT"],
            access_key=os.environ["CMC_ARTIFACT_ACCESS_KEY"],
            secret_key=os.environ["CMC_ARTIFACT_SECRET_KEY"],
            secure=False,
        ),
        "cmc-artifacts",
    )
    source = LiveFieldArtifactSource(mirror, store)
    members: list[CorpusMember] = []
    material_digest = canonical_case_digest(
        {"youngs_modulus_gpa": 200, "poissons_ratio": 0.3, "plane": "strain"}
    )
    for run_id in run_ids:
        snapshot = mirror.inspect(run_id)
        response = FieldArtifact(source).field_artifact(run_id)
        if (
            response.get("state") != "available"
            or snapshot.outcome != "solved"
            or snapshot.evidence_disposition != "accepted"
        ):
            raise SystemExit(f"{run_id} is not an accepted reference field set.")
        artifacts = response["payload"]["provenance"]["artifact_digests"]
        card = mirror.case_card(run_id)
        field_set_digest = sha256(
            json.dumps(artifacts, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        problem_card = {
            key: value
            for key, value in card.items()
            if key not in {"case_id", "workflow_key"}
        }
        members.append(
            CorpusMember(
                card["case_id"],
                field_set_digest,
                True,
                canonical_case_digest(problem_card),
                artifacts["field/displacement/pair-map"],
                material_digest,
            )
        )
    frozen = CorpusCurator().freeze_and_publish(
        CorpusRequest("r0-elastic/v1", tuple(members)), store
    )
    if not isinstance(frozen, tuple):
        raise SystemExit(f"Corpus refused: {frozen.reason}")
    receipt, artifact = frozen
    print(
        f"r0-corpus digest={receipt.digest} artifact={artifact.sha256} members={','.join(member.case_id for member in receipt.members)}"
    )


if __name__ == "__main__":
    main()

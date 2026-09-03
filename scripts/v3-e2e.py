#!/usr/bin/env python3
"""Run one local V3 reference-solver attempt against Compose services."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from minio import Minio

from app.case_executor import CaseExecutor, LocalComposeRunner
from app.field_artifact import FieldArtifact
from app.run_mirror import MinioDigestStore, PostgresRunMirror
from app.v3_api import LiveFieldArtifactSource
from app.workflow_compiler import V1_WORKFLOW


def main() -> None:
    dsn = os.environ["CMC_RUN_MIRROR_DSN"]
    mirror = PostgresRunMirror(dsn)
    store = MinioDigestStore(
        Minio(
            os.environ["CMC_ARTIFACT_ENDPOINT"],
            access_key=os.environ["CMC_ARTIFACT_ACCESS_KEY"],
            secret_key=os.environ["CMC_ARTIFACT_SECRET_KEY"],
            secure=False,
        ),
        "cmc-artifacts",
    )
    case_id = os.environ.get("CMC_V3_E2E_CASE_ID", "edge-cracked-plate-v1")
    run = mirror.submit(
        {"case_id": case_id, "version": 1, "workflow_key": V1_WORKFLOW},
        f"v3-e2e-{uuid4()}",
    )
    result = CaseExecutor(LocalComposeRunner(), mirror, store).execute_next(
        Path(".local/v3-e2e-scratch"), run.run_id
    )
    assert result is not None
    attempt, execution = result
    final = mirror.inspect(run.run_id)
    assert attempt.run_id == run.run_id
    assert execution.exit_code == 0, execution.stderr
    assert (final.lifecycle, final.outcome) == ("terminal", "solved")
    assert mirror.detail_page(run.run_id, "publish")[0]
    response = FieldArtifact(LiveFieldArtifactSource(mirror, store)).field_artifact(run.run_id)
    assert response["state"] == "available", response
    assert response["payload"]["field"]["units"] == "mm"
    assert "field/displacement/hdf5" in response["payload"]["provenance"]["artifact_digests"]
    print(f"v3-e2e run={run.run_id} outcome={final.outcome} workflow={V1_WORKFLOW}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run one local V3 reference-solver attempt against Compose services."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from minio import Minio

from app.case_executor import CaseExecutor, LocalComposeRunner
from app.run_mirror import MinioDigestStore, PostgresRunMirror
from app.field_artifact import FieldArtifact
from app.v3_api import LiveFieldArtifactSource


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
    runner_key = os.environ.get("CMC_V3_E2E_RUNNER", "reference-solver")
    run = mirror.submit(
        {"case_id": "v3-e2e-reference", "version": 1, "runner_key": runner_key},
        f"v3-e2e-{uuid4()}",
    )
    result = CaseExecutor(LocalComposeRunner(), mirror, store).execute_next(
        Path(".local/v3-e2e-scratch")
    )
    assert result is not None
    attempt, execution = result
    final = mirror.inspect(run.run_id)
    assert attempt.run_id == run.run_id
    assert execution.exit_code == 0, execution.stderr
    expected = "solved" if runner_key == "r0-field-export" else "indeterminate"
    assert (final.lifecycle, final.outcome) == ("terminal", expected)
    assert mirror.detail_page(run.run_id, "verify")[0]
    if runner_key == "r0-field-export":
        response = FieldArtifact(LiveFieldArtifactSource(mirror, store)).field_artifact(run.run_id)
        assert response["state"] == "available", response
        assert response["payload"]["field"]["units"] == "mm"
        assert "field/displacement/hdf5" in response["payload"]["provenance"]["artifact_digests"]
    print(f"v3-e2e run={run.run_id} outcome={final.outcome} runner={runner_key}")


if __name__ == "__main__":
    main()

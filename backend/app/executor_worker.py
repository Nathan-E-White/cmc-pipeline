"""Local-only serial worker for admitted V3 runs."""

from __future__ import annotations

import os
import time
from logging import getLogger
from pathlib import Path

from minio import Minio

from app.case_executor import CaseExecutor, LocalComposeRunner
from app.run_mirror import MinioDigestStore, PostgresRunMirror

logger = getLogger(__name__)


def main() -> None:
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
    runner = LocalComposeRunner()
    executor = CaseExecutor(runner, mirror, store)
    scratch = Path(os.environ.get("CMC_EXECUTOR_SCRATCH", "/scratch"))
    while True:
        try:
            for attempt in mirror.running_attempts():
                if not runner.container_exists(attempt.container_name):
                    mirror.recover_missing_container(attempt.run_id, attempt.attempt_number)
            executor.execute_next(scratch)
        except Exception:
            # The executor has already recorded the terminal attempt failure; keep
            # the single worker available for the next submitted run.
            logger.exception("Executor loop recovered after a recorded attempt failure")
        time.sleep(0.5)


if __name__ == "__main__":
    main()

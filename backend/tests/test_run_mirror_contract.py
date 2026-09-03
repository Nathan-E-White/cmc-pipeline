import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from minio import Minio

from app.run_mirror import (
    ArtifactIntegrityError,
    ArtifactReceipt,
    MinioDigestStore,
    PostgresRunMirror,
    RunMirrorError,
)

DSN = os.environ.get("CMC_RUN_MIRROR_DSN")
ENDPOINT = os.environ.get("CMC_ARTIFACT_ENDPOINT")
ACCESS_KEY = os.environ.get("CMC_ARTIFACT_ACCESS_KEY")
SECRET_KEY = os.environ.get("CMC_ARTIFACT_SECRET_KEY")
pytestmark = pytest.mark.skipif(
    not all([DSN, ENDPOINT, ACCESS_KEY, SECRET_KEY]),
    reason="requires local Compose services",
)


@pytest.fixture
def run_mirror() -> PostgresRunMirror:
    assert DSN is not None
    return PostgresRunMirror(DSN)


@pytest.fixture
def artifact_store() -> MinioDigestStore:
    assert ENDPOINT is not None
    assert ACCESS_KEY is not None
    assert SECRET_KEY is not None
    return MinioDigestStore(
        Minio(ENDPOINT, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False),
        "cmc-artifacts",
    )


def r0_card(case_id: str = "r0-elastic-displacement-e200-v1") -> dict[str, object]:
    return {"case_id": case_id, "version": 1, "workflow_key": "r0-reference-field-export/v1"}


def v1_card() -> dict[str, object]:
    return {
        "case_id": "edge-cracked-plate-v1",
        "version": 1,
        "workflow_key": "reference-field-export/v1",
    }


def test_submission_admits_the_existing_v1_field_export_without_a_runner_key(
    run_mirror: PostgresRunMirror,
) -> None:
    run = run_mirror.submit(v1_card(), f"contract-submit-v1-{uuid4()}")

    assert run.lifecycle == "submitted"
    attempt = run_mirror.claim_next_attempt(run.run_id)
    assert attempt is not None
    assert attempt.case_card == v1_card()


def test_submission_is_idempotent_and_reconstructs_after_a_new_adapter(
    run_mirror: PostgresRunMirror,
) -> None:
    card = r0_card()
    key = f"contract-restart-r0-{uuid4()}"
    first = run_mirror.submit(card, key)

    assert run_mirror.submit(card, key) == first
    assert PostgresRunMirror(DSN).inspect(first.run_id) == first
    assert [
        (event.run_sequence, event.event_type)
        for event in PostgresRunMirror(DSN).stream(first.run_id)
    ] == [(1, "run-submitted")]


def test_queued_cancel_is_an_ordered_terminal_lifecycle_fact_and_refreshes_its_projection(
    run_mirror: PostgresRunMirror,
) -> None:
    run = run_mirror.submit(r0_card(), f"contract-cancel-r0-{uuid4()}")

    cancelled = run_mirror.request_cancel(run.run_id)
    assert (cancelled.lifecycle, cancelled.outcome) == ("terminal", "cancelled")
    events = [(event.run_sequence, event.event_type) for event in run_mirror.stream(run.run_id)]
    assert events == [
        (1, "run-submitted"),
        (2, "queued-cancelled"),
    ]
    assert [
        (event.run_sequence, event.event_type) for event in run_mirror.stream(run.run_id, 1)
    ] == [(2, "queued-cancelled")]
    assert run_mirror.request_cancel(run.run_id) == run_mirror.inspect(run.run_id)
    assert [(event.run_sequence, event.event_type) for event in run_mirror.stream(run.run_id)] == [
        (1, "run-submitted"),
        (2, "queued-cancelled"),
    ]


def test_claim_finish_and_detail_pages_persist_a_serial_attempt(
    run_mirror: PostgresRunMirror,
) -> None:
    run = run_mirror.submit(r0_card(), f"contract-claim-r0-{uuid4()}")

    attempt = run_mirror.claim_next_attempt(run.run_id)

    assert attempt is not None
    assert (attempt.run_id, attempt.attempt_number, attempt.state) == (run.run_id, 1, "running")
    finished = run_mirror.finish_attempt(run.run_id, 1, 0)
    page, next_before = run_mirror.detail_page(run.run_id, "publish", limit=5)
    summaries = run_mirror.summaries()
    assert (finished.lifecycle, finished.outcome) == ("terminal", "indeterminate")
    assert next_before is None
    assert page[0]["label"] == "attempt finished"
    assert any(
        summary["run_id"] == run.run_id and summary["revision"] >= 3 for summary in summaries
    )


def test_missing_container_recovery_records_failure_without_retry(
    run_mirror: PostgresRunMirror,
) -> None:
    run = run_mirror.submit(r0_card(), f"contract-recovery-r0-{uuid4()}")
    run_mirror.claim_next_attempt(run.run_id)

    recovered = run_mirror.recover_missing_container(run.run_id, 1)

    assert (recovered.lifecycle, recovered.outcome, recovered.current_attempt) == (
        "terminal",
        "failed",
        1,
    )


def test_idempotency_key_cannot_represent_two_case_cards(
    run_mirror: PostgresRunMirror,
) -> None:
    key = f"contract-conflict-r0-{uuid4()}"
    run_mirror.submit(r0_card("r0-elastic-displacement-e180-v1"), key)

    with pytest.raises(RunMirrorError, match="different case"):
        run_mirror.submit(r0_card("r0-elastic-displacement-e220-v1"), key)


def test_concurrent_submission_with_one_key_converges_on_one_run(
    run_mirror: PostgresRunMirror,
) -> None:
    card = r0_card()
    key = f"contract-concurrent-r0-{uuid4()}"

    with ThreadPoolExecutor(max_workers=2) as executor:
        snapshots = list(
            executor.map(
                lambda _: run_mirror.submit(card, key),
                range(2),
            )
        )

    assert snapshots[0] == snapshots[1]


def test_minio_artifact_is_content_addressed_and_recorded(
    run_mirror: PostgresRunMirror,
    artifact_store: MinioDigestStore,
) -> None:
    run = run_mirror.submit(r0_card(), f"contract-artifact-r0-{uuid4()}")
    content = b"declared local development evidence\\n"
    receipt = artifact_store.put_bytes(content, "text/plain")

    run_mirror.record_artifact(run.run_id, "case-card-note", receipt)

    assert artifact_store.get_bytes(receipt) == content
    assert receipt == ArtifactReceipt(
        receipt.sha256, len(content), "text/plain", f"sha256/{receipt.sha256}"
    )
    with pytest.raises(ArtifactIntegrityError, match="SHA-256"):
        artifact_store.get_bytes(
            ArtifactReceipt("0" * 64, receipt.byte_length, receipt.media_type, receipt.storage_key)
        )

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


def test_submission_is_idempotent_and_reconstructs_after_a_new_adapter(
    run_mirror: PostgresRunMirror,
) -> None:
    card = {
        "case_id": "r0-smoke",
        "version": 1,
        "declared_exclusions": ["calibration"],
    }
    first = run_mirror.submit(card, "contract-restart-r0")

    assert run_mirror.submit(card, "contract-restart-r0") == first
    assert PostgresRunMirror(DSN).inspect(first.run_id) == first
    assert [
        (event.run_sequence, event.event_type)
        for event in PostgresRunMirror(DSN).stream(first.run_id)
    ] == [(1, "run-submitted")]


def test_cancel_request_is_an_ordered_persistent_lifecycle_fact(
    run_mirror: PostgresRunMirror,
) -> None:
    run = run_mirror.submit({"case_id": "r0-cancel", "version": 1}, "contract-cancel-r0")

    assert run_mirror.request_cancel(run.run_id).lifecycle == "cancel-requested"
    events = [(event.run_sequence, event.event_type) for event in run_mirror.stream(run.run_id)]
    assert events == [
        (1, "run-submitted"),
        (2, "cancel-requested"),
    ]
    assert [
        (event.run_sequence, event.event_type) for event in run_mirror.stream(run.run_id, 1)
    ] == [(2, "cancel-requested")]
    assert run_mirror.request_cancel(run.run_id) == run_mirror.inspect(run.run_id)
    assert [(event.run_sequence, event.event_type) for event in run_mirror.stream(run.run_id)] == [
        (1, "run-submitted"),
        (2, "cancel-requested"),
    ]


def test_idempotency_key_cannot_represent_two_case_cards(
    run_mirror: PostgresRunMirror,
) -> None:
    run_mirror.submit({"case_id": "r0-a", "version": 1}, "contract-conflict-r0")

    with pytest.raises(RunMirrorError, match="different case"):
        run_mirror.submit({"case_id": "r0-b", "version": 1}, "contract-conflict-r0")


def test_concurrent_submission_with_one_key_converges_on_one_run(
    run_mirror: PostgresRunMirror,
) -> None:
    card = {"case_id": "r0-concurrent", "version": 1}
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
    run = run_mirror.submit({"case_id": "r0-artifact", "version": 1}, "contract-artifact-r0")
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

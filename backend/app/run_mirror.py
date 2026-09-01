"""Persistent V3 operational records; V1 fixture workflow is intentionally separate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

import psycopg
from minio import Minio
from minio.error import S3Error


class RunMirrorError(Exception):
    """Raised when a caller asks the Run Mirror to violate its contract."""


class ArtifactIntegrityError(RunMirrorError):
    """Raised when content at an address does not match its claimed digest."""


@dataclass(frozen=True)
class RunSnapshot:
    run_id: str
    case_digest: str
    lifecycle: str
    outcome: str | None
    current_attempt: int
    evidence_disposition: str | None = None


@dataclass(frozen=True)
class RunEvent:
    run_sequence: int
    attempt_number: int
    sequence: int
    event_type: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ArtifactReceipt:
    sha256: str
    byte_length: int
    media_type: str
    storage_key: str


@dataclass(frozen=True)
class RunObservation:
    """One validated executor observation; the Run Mirror makes it durable atomically."""

    phase_key: str
    event_type: str
    payload: dict[str, Any]
    phase_state: str
    headline: dict[str, Any]
    trend: dict[str, Any]
    warnings: list[str]
    container_observed_at: str | None = None
    solver_evidence_at: str | None = None
    lifecycle: str | None = None
    outcome: str | None = None
    evidence_disposition: str | None = None
    artifacts: tuple[tuple[str, ArtifactReceipt], ...] = ()


def canonical_case_digest(case_card: dict[str, Any]) -> str:
    if not isinstance(case_card, dict):
        raise RunMirrorError("A case card must be a JSON object.")
    encoded = json.dumps(
        case_card, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return sha256(encoded).hexdigest()


class MinioDigestStore:
    """Hide MinIO's object API behind immutable SHA-256-addressed bytes."""

    def __init__(self, client: Minio, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put_bytes(self, content: bytes, media_type: str) -> ArtifactReceipt:
        digest = sha256(content).hexdigest()
        key = f"sha256/{digest}"
        self.ensure_bucket()
        try:
            self._client.stat_object(self._bucket, key)
        except S3Error as error:
            if error.code != "NoSuchKey":
                raise
            self._client.put_object(
                self._bucket, key, BytesIO(content), len(content), content_type=media_type
            )
        return ArtifactReceipt(digest, len(content), media_type, key)

    def get_bytes(self, receipt: ArtifactReceipt) -> bytes:
        response = self._client.get_object(self._bucket, receipt.storage_key)
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()
        if len(content) != receipt.byte_length or sha256(content).hexdigest() != receipt.sha256:
            raise ArtifactIntegrityError(
                "Stored artifact does not match its declared SHA-256 identity."
            )
        return content


class PostgresRunMirror:
    """Postgres adapter for the Run Mirror interface and event/artifact record."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def submit(self, case_card: dict[str, Any], idempotency_key: str) -> RunSnapshot:
        if not idempotency_key:
            raise RunMirrorError("An idempotency key is required.")
        digest = canonical_case_digest(case_card)
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO case_cards (case_digest, card) VALUES (%s, %s) "
                "ON CONFLICT (case_digest) DO NOTHING",
                (digest, json.dumps(case_card, sort_keys=True)),
            )
            run_id = uuid4()
            cursor.execute(
                "INSERT INTO runs (run_id, case_digest, idempotency_key, lifecycle) "
                "VALUES (%s, %s, %s, 'submitted') ON CONFLICT (idempotency_key) "
                "DO NOTHING RETURNING run_id, case_digest, lifecycle, outcome, current_attempt, evidence_disposition",
                (run_id, digest, idempotency_key),
            )
            created = cursor.fetchone()
            if created is None:
                cursor.execute(
                    "SELECT run_id, case_digest, lifecycle, outcome, current_attempt, evidence_disposition "
                    "FROM runs WHERE idempotency_key = %s",
                    (idempotency_key,),
                )
                existing = cursor.fetchone()
                if existing is None:
                    raise RunMirrorError("Idempotency admission did not produce a run record.")
                snapshot = self._snapshot(existing)
                if snapshot.case_digest != digest:
                    raise RunMirrorError(
                        "Idempotency key was previously submitted for a different case card."
                    )
                return snapshot
            cursor.execute(
                "INSERT INTO run_events (run_id, attempt_number, run_sequence, sequence, "
                "event_type, payload) VALUES (%s, 1, 1, 1, 'run-submitted', %s)",
                (run_id, json.dumps({"case_digest": digest})),
            )
            cursor.execute(
                "INSERT INTO run_summary_projections (run_id, revision, lifecycle) VALUES (%s, 1, 'submitted')",
                (run_id,),
            )
            return RunSnapshot(str(run_id), digest, "submitted", None, 1)

    def inspect(self, run_id: str) -> RunSnapshot:
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id, case_digest, lifecycle, outcome, current_attempt, evidence_disposition "
                "FROM runs WHERE run_id = %s",
                (UUID(run_id),),
            )
            row = cursor.fetchone()
        if row is None:
            raise RunMirrorError("Run does not exist.")
        return self._snapshot(row)

    def request_cancel(self, run_id: str) -> RunSnapshot:
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id, case_digest, lifecycle, outcome, current_attempt, evidence_disposition "
                "FROM runs WHERE run_id = %s FOR UPDATE",
                (UUID(run_id),),
            )
            row = cursor.fetchone()
            if row is None:
                raise RunMirrorError("Run does not exist.")
            snapshot = self._snapshot(row)
            if snapshot.lifecycle in {"cancel-requested", "terminal"}:
                return snapshot
            cursor.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1, (SELECT "
                "COALESCE(MAX(run_sequence), 0) + 1 FROM run_events WHERE run_id = %s) "
                "FROM run_events WHERE run_id = %s AND attempt_number = %s",
                (UUID(run_id), UUID(run_id), snapshot.current_attempt),
            )
            sequence, run_sequence = cursor.fetchone()
            cursor.execute(
                "UPDATE runs SET lifecycle = 'cancel-requested', updated_at = now() "
                "WHERE run_id = %s",
                (UUID(run_id),),
            )
            cursor.execute(
                "INSERT INTO run_events (run_id, attempt_number, run_sequence, sequence, "
                "event_type, payload) VALUES (%s, %s, %s, %s, 'cancel-requested', "
                "'{}'::jsonb)",
                (UUID(run_id), snapshot.current_attempt, run_sequence, sequence),
            )
        return RunSnapshot(
            snapshot.run_id,
            snapshot.case_digest,
            "cancel-requested",
            None,
            snapshot.current_attempt,
        )

    def stream(self, run_id: str, after_sequence: int = 0) -> list[RunEvent]:
        if after_sequence < 0:
            raise RunMirrorError("after_sequence cannot be negative.")
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_sequence, attempt_number, sequence, event_type, payload "
                "FROM run_events WHERE run_id = %s AND run_sequence > %s "
                "ORDER BY run_sequence",
                (UUID(run_id), after_sequence),
            )
            rows = cursor.fetchall()
        return [RunEvent(row[0], row[1], row[2], row[3], row[4]) for row in rows]

    def record_artifact(self, run_id: str, role: str, artifact: ArtifactReceipt) -> None:
        if not role:
            raise RunMirrorError("An artifact role is required.")
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO artifacts (sha256, byte_length, media_type, storage_key) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (sha256) DO NOTHING",
                (artifact.sha256, artifact.byte_length, artifact.media_type, artifact.storage_key),
            )
            cursor.execute(
                "INSERT INTO run_artifacts (run_id, role, sha256) VALUES (%s, %s, %s) "
                "ON CONFLICT (run_id, role) DO UPDATE SET sha256 = EXCLUDED.sha256",
                (UUID(run_id), role, artifact.sha256),
            )

    def record(self, run_id: str, attempt_number: int, observation: RunObservation) -> RunSnapshot:
        """Append evidence and refresh only its compact projection in one transaction."""
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id, case_digest, lifecycle, outcome, current_attempt, evidence_disposition "
                "FROM runs WHERE run_id = %s FOR UPDATE",
                (UUID(run_id),),
            )
            row = cursor.fetchone()
            if row is None:
                raise RunMirrorError("Run does not exist.")
            snapshot = self._snapshot(row)
            if snapshot.current_attempt != attempt_number:
                raise RunMirrorError("Observation names a non-current attempt.")
            cursor.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1, COALESCE(MAX(run_sequence), 0) + 1 "
                "FROM run_events WHERE run_id = %s",
                (UUID(run_id),),
            )
            sequence, revision = cursor.fetchone()
            cursor.execute(
                "INSERT INTO run_events (run_id, attempt_number, run_sequence, sequence, phase_key, event_type, payload) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (UUID(run_id), attempt_number, revision, sequence, observation.phase_key,
                 observation.event_type, json.dumps(observation.payload, sort_keys=True)),
            )
            lifecycle = observation.lifecycle or snapshot.lifecycle
            outcome = observation.outcome if observation.lifecycle == "terminal" else snapshot.outcome
            disposition = observation.evidence_disposition or snapshot.evidence_disposition
            cursor.execute(
                "UPDATE runs SET lifecycle = %s, outcome = %s, evidence_disposition = %s, updated_at = now() "
                "WHERE run_id = %s",
                (lifecycle, outcome, disposition, UUID(run_id)),
            )
            cursor.execute(
                "INSERT INTO run_summary_projections (run_id, revision, lifecycle, outcome, evidence_disposition, current_phase_key) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (run_id) DO UPDATE SET "
                "revision = EXCLUDED.revision, lifecycle = EXCLUDED.lifecycle, outcome = EXCLUDED.outcome, "
                "evidence_disposition = EXCLUDED.evidence_disposition, current_phase_key = EXCLUDED.current_phase_key, updated_at = now()",
                (UUID(run_id), revision, lifecycle, outcome, disposition, observation.phase_key),
            )
            cursor.execute(
                "INSERT INTO run_phase_summary_projections (run_id, phase_key, revision, state, headline, trend, warnings, last_container_observed_at, last_solver_evidence_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (run_id, phase_key) DO UPDATE SET "
                "revision = EXCLUDED.revision, state = EXCLUDED.state, headline = EXCLUDED.headline, trend = EXCLUDED.trend, warnings = EXCLUDED.warnings, "
                "last_container_observed_at = EXCLUDED.last_container_observed_at, last_solver_evidence_at = EXCLUDED.last_solver_evidence_at",
                (UUID(run_id), observation.phase_key, revision, observation.phase_state,
                 json.dumps(observation.headline), json.dumps(observation.trend), json.dumps(observation.warnings),
                 observation.container_observed_at, observation.solver_evidence_at),
            )
            for role, artifact in observation.artifacts:
                cursor.execute(
                    "INSERT INTO artifacts (sha256, byte_length, media_type, storage_key) VALUES (%s, %s, %s, %s) ON CONFLICT (sha256) DO NOTHING",
                    (artifact.sha256, artifact.byte_length, artifact.media_type, artifact.storage_key),
                )
                cursor.execute(
                    "INSERT INTO run_artifacts (run_id, role, sha256) VALUES (%s, %s, %s) ON CONFLICT (run_id, role) DO UPDATE SET sha256 = EXCLUDED.sha256",
                    (UUID(run_id), role, artifact.sha256),
                )
        return RunSnapshot(snapshot.run_id, snapshot.case_digest, lifecycle, outcome, attempt_number, disposition)

    @staticmethod
    def _snapshot(row: tuple[Any, ...]) -> RunSnapshot:
        return RunSnapshot(str(row[0]), row[1], row[2], row[3], row[4], row[5] if len(row) > 5 else None)

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


@dataclass(frozen=True)
class RunAttempt:
    """A locally admitted, recoverable execution attempt."""

    run_id: str
    attempt_number: int
    runner_key: str
    container_name: str
    state: str


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
            runner_key = case_card.get("runner_key", "reference-solver")
            if runner_key != "reference-solver":
                raise RunMirrorError(
                    "The local executor only admits declared runner 'reference-solver'."
                )
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
            cursor.execute(
                "INSERT INTO run_attempts (run_id, attempt_number, runner_key, container_name, state) "
                "VALUES (%s, 1, %s, %s, 'queued')",
                (run_id, runner_key, f"cmc-v3-{run_id}-attempt-1"),
            )
            return RunSnapshot(str(run_id), digest, "submitted", None, 1)

    def claim_next_attempt(self, run_id: str | None = None) -> RunAttempt | None:
        """Atomically admit one queued run; one process therefore remains serial."""
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            target = " AND a.run_id = %s" if run_id else ""
            cursor.execute(
                "SELECT a.run_id, a.attempt_number, a.runner_key, a.container_name, a.state "
                "FROM run_attempts a JOIN runs r ON r.run_id = a.run_id "
                f"WHERE a.state = 'queued' AND r.lifecycle = 'submitted'{target} "
                "ORDER BY r.created_at FOR UPDATE OF a, r SKIP LOCKED LIMIT 1",
                (UUID(run_id),) if run_id else (),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            run_id = row[0]
            cursor.execute(
                "UPDATE run_attempts SET state = 'running', started_at = now(), last_container_observed_at = now() "
                "WHERE run_id = %s AND attempt_number = %s",
                (run_id, row[1]),
            )
            cursor.execute(
                "UPDATE runs SET lifecycle = 'running', updated_at = now() WHERE run_id = %s",
                (run_id,),
            )
            revision = self._next_run_sequence(cursor, run_id)
            cursor.execute(
                "INSERT INTO run_events (run_id, attempt_number, run_sequence, sequence, phase_key, event_type, payload) "
                "VALUES (%s, %s, %s, %s, 'admitted', 'attempt-started', %s)",
                (
                    run_id,
                    row[1],
                    revision,
                    self._next_attempt_sequence(cursor, run_id, row[1]),
                    json.dumps({"runner_key": row[2], "container_name": row[3]}),
                ),
            )
            cursor.execute(
                "UPDATE run_summary_projections SET revision = %s, lifecycle = 'running', current_phase_key = 'admitted', updated_at = now() WHERE run_id = %s",
                (revision, run_id),
            )
            cursor.execute(
                "INSERT INTO run_phase_summary_projections (run_id, phase_key, revision, state, headline, trend, warnings, last_container_observed_at) "
                "VALUES (%s, 'admitted', %s, 'completed', %s, '{}'::jsonb, '[]'::jsonb, now()) "
                "ON CONFLICT (run_id, phase_key) DO UPDATE SET revision = EXCLUDED.revision, state = EXCLUDED.state, headline = EXCLUDED.headline, last_container_observed_at = EXCLUDED.last_container_observed_at",
                (
                    run_id,
                    revision,
                    json.dumps({"text": "Local serial executor admitted this attempt."}),
                ),
            )
        return RunAttempt(str(row[0]), row[1], row[2], row[3], "running")

    def finish_attempt(self, run_id: str, attempt_number: int, exit_code: int) -> RunSnapshot:
        """Record process completion without turning verification into a solution claim."""
        outcome = "indeterminate" if exit_code == 0 else "failed"
        event_type = "attempt-finished" if exit_code == 0 else "attempt-failed"
        return self.record(
            run_id,
            attempt_number,
            RunObservation(
                phase_key="publish",
                event_type=event_type,
                payload={"exit_code": exit_code},
                phase_state="completed" if exit_code == 0 else "failed",
                headline={"exit_code": exit_code},
                trend={},
                warnings=[
                    "Declared verification completed; it does not establish a solved physical case."
                ]
                if exit_code == 0
                else ["Runner exited nonzero; artifacts remain available for review."],
                lifecycle="terminal",
                outcome=outcome,
                evidence_disposition="indeterminate",
            ),
        )

    def recover_missing_container(self, run_id: str, attempt_number: int) -> RunSnapshot:
        """A vanished named container is a failed local attempt, never an automatic retry."""
        return self.finish_attempt(run_id, attempt_number, 125)

    def running_attempts(self) -> list[RunAttempt]:
        """Return local attempts that must still have their declared named container."""
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_id, attempt_number, runner_key, container_name, state "
                "FROM run_attempts WHERE state = 'running' ORDER BY started_at"
            )
            rows = cursor.fetchall()
        return [RunAttempt(str(row[0]), row[1], row[2], row[3], row[4]) for row in rows]

    def register_events(self, after_sequence: int = 0) -> list[dict[str, int | str]]:
        """Return global register notices; local run revisions are not a stream cursor."""
        if after_sequence < 0:
            raise RunMirrorError("register sequence cannot be negative.")
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT register_sequence, run_id FROM run_events "
                "WHERE register_sequence > %s ORDER BY register_sequence",
                (after_sequence,),
            )
            rows = cursor.fetchall()
        return [{"register_sequence": row[0], "run_id": str(row[1])} for row in rows]

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
                "SELECT state FROM run_attempts WHERE run_id = %s AND attempt_number = %s",
                (UUID(run_id), snapshot.current_attempt),
            )
            attempt = cursor.fetchone()
            sequence = self._next_attempt_sequence(cursor, UUID(run_id), snapshot.current_attempt)
            run_sequence = self._next_run_sequence(cursor, UUID(run_id))
            lifecycle, outcome, event_type = (
                ("terminal", "cancelled", "queued-cancelled")
                if attempt is None or attempt[0] == "queued"
                else ("cancel-requested", None, "cancel-requested")
            )
            cursor.execute(
                "UPDATE runs SET lifecycle = %s, outcome = %s, updated_at = now() WHERE run_id = %s",
                (lifecycle, outcome, UUID(run_id)),
            )
            if lifecycle == "terminal":
                cursor.execute(
                    "UPDATE run_attempts SET state = 'terminal', finished_at = now() "
                    "WHERE run_id = %s AND attempt_number = %s",
                    (UUID(run_id), snapshot.current_attempt),
                )
            cursor.execute(
                "INSERT INTO run_events (run_id, attempt_number, run_sequence, sequence, "
                "event_type, payload) VALUES (%s, %s, %s, %s, %s, "
                "'{}'::jsonb)",
                (UUID(run_id), snapshot.current_attempt, run_sequence, sequence, event_type),
            )
            cursor.execute(
                "UPDATE run_summary_projections SET revision = %s, lifecycle = %s, outcome = %s, current_phase_key = 'admitted', updated_at = now() WHERE run_id = %s",
                (run_sequence, lifecycle, outcome, UUID(run_id)),
            )
            cursor.execute(
                "INSERT INTO run_phase_summary_projections (run_id, phase_key, revision, state, headline, trend, warnings) "
                "VALUES (%s, 'admitted', %s, %s, %s, '{}'::jsonb, '[]'::jsonb) "
                "ON CONFLICT (run_id, phase_key) DO UPDATE SET revision = EXCLUDED.revision, state = EXCLUDED.state, headline = EXCLUDED.headline",
                (
                    UUID(run_id),
                    run_sequence,
                    "cancelled" if lifecycle == "terminal" else "running",
                    json.dumps({"text": event_type}),
                ),
            )
        return RunSnapshot(
            snapshot.run_id,
            snapshot.case_digest,
            lifecycle,
            outcome,
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

    def summaries(self, after_revision: int = 0) -> list[dict[str, Any]]:
        """Return compact projections only; raw event payloads stay out of the register."""
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            return self._summary_records(cursor, after_revision)

    def register_snapshot(self) -> tuple[list[dict[str, Any]], int]:
        """Capture the cursor then its compact projection in one database snapshot."""
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(register_sequence), 0) FROM run_events")
            register_sequence = cursor.fetchone()[0]
            return self._summary_records(cursor, 0), register_sequence

    @staticmethod
    def _summary_records(cursor: Any, after_revision: int) -> list[dict[str, Any]]:
        cursor.execute(
            "SELECT s.run_id, s.revision, s.lifecycle, s.outcome, s.evidence_disposition, "
            "s.current_phase_key, p.state, p.headline, p.trend, p.warnings, "
            "p.last_container_observed_at, p.last_solver_evidence_at "
            "FROM run_summary_projections s LEFT JOIN run_phase_summary_projections p "
            "ON p.run_id = s.run_id AND p.phase_key = s.current_phase_key "
            "WHERE s.revision > %s ORDER BY s.updated_at, s.run_id",
            (after_revision,),
        )
        rows = cursor.fetchall()
        return [
            {
                "run_id": str(row[0]),
                "revision": row[1],
                "lifecycle": row[2],
                "outcome": row[3],
                "evidence_disposition": row[4],
                "current_phase_key": row[5],
                "state": row[6],
                "headline": row[7] or {},
                "trend": row[8] or {},
                "warnings": row[9] or [],
                "container_observed_at": row[10].isoformat() if row[10] else None,
                "solver_evidence_at": row[11].isoformat() if row[11] else None,
            }
            for row in rows
        ]

    def detail_page(
        self, run_id: str, phase_key: str, before_sequence: int | None = None, limit: int = 5
    ) -> tuple[list[dict[str, Any]], int | None]:
        """Load a bounded reverse-chronological page of normalized phase evidence."""
        if not phase_key or not 1 <= limit <= 100:
            raise RunMirrorError("A phase key and page size from 1 to 100 are required.")
        where = "AND phase_key = %s"
        params: list[Any] = [UUID(run_id), phase_key]
        if before_sequence is not None:
            where += " AND run_sequence < %s"
            params.append(before_sequence)
        params.append(limit + 1)
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT run_sequence, event_type, payload, occurred_at FROM run_events "
                f"WHERE run_id = %s {where} ORDER BY run_sequence DESC LIMIT %s",
                params,
            )
            rows = cursor.fetchall()
        has_more = len(rows) > limit
        page = rows[:limit]
        next_before = page[-1][0] if has_more and page else None
        return (
            [self._detail_record(row) for row in page],
            next_before,
        )

    def record_artifact(self, run_id: str, role: str, artifact: ArtifactReceipt) -> None:
        if not role:
            raise RunMirrorError("An artifact role is required.")
        with psycopg.connect(self._dsn) as connection, connection.cursor() as cursor:
            self._link_artifact(cursor, UUID(run_id), role, artifact)

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
            sequence = self._next_attempt_sequence(cursor, UUID(run_id), attempt_number)
            revision = self._next_run_sequence(cursor, UUID(run_id))
            cursor.execute(
                "INSERT INTO run_events (run_id, attempt_number, run_sequence, sequence, phase_key, event_type, payload) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    UUID(run_id),
                    attempt_number,
                    revision,
                    sequence,
                    observation.phase_key,
                    observation.event_type,
                    json.dumps(observation.payload, sort_keys=True),
                ),
            )
            lifecycle = observation.lifecycle or snapshot.lifecycle
            outcome = (
                observation.outcome if observation.lifecycle == "terminal" else snapshot.outcome
            )
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
                (
                    UUID(run_id),
                    observation.phase_key,
                    revision,
                    observation.phase_state,
                    json.dumps(observation.headline),
                    json.dumps(observation.trend),
                    json.dumps(observation.warnings),
                    observation.container_observed_at,
                    observation.solver_evidence_at,
                ),
            )
            if observation.lifecycle == "terminal":
                cursor.execute(
                    "UPDATE run_attempts SET state = 'terminal', finished_at = now(), exit_code = COALESCE((%s::jsonb->>'exit_code')::integer, exit_code) "
                    "WHERE run_id = %s AND attempt_number = %s",
                    (json.dumps(observation.payload), UUID(run_id), attempt_number),
                )
            for role, artifact in observation.artifacts:
                self._link_artifact(cursor, UUID(run_id), role, artifact)
        return RunSnapshot(
            snapshot.run_id, snapshot.case_digest, lifecycle, outcome, attempt_number, disposition
        )

    @staticmethod
    def _snapshot(row: tuple[Any, ...]) -> RunSnapshot:
        return RunSnapshot(
            str(row[0]), row[1], row[2], row[3], row[4], row[5] if len(row) > 5 else None
        )

    @staticmethod
    def _next_attempt_sequence(cursor: Any, run_id: UUID, attempt_number: int) -> int:
        cursor.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM run_events WHERE run_id = %s AND attempt_number = %s",
            (run_id, attempt_number),
        )
        return cursor.fetchone()[0]

    @staticmethod
    def _next_run_sequence(cursor: Any, run_id: UUID) -> int:
        cursor.execute(
            "SELECT COALESCE(MAX(run_sequence), 0) + 1 FROM run_events WHERE run_id = %s", (run_id,)
        )
        return cursor.fetchone()[0]

    @staticmethod
    def _link_artifact(cursor: Any, run_id: UUID, role: str, artifact: ArtifactReceipt) -> None:
        cursor.execute(
            "INSERT INTO artifacts (sha256, byte_length, media_type, storage_key) VALUES (%s, %s, %s, %s) ON CONFLICT (sha256) DO NOTHING",
            (artifact.sha256, artifact.byte_length, artifact.media_type, artifact.storage_key),
        )
        cursor.execute(
            "INSERT INTO run_artifacts (run_id, role, sha256) VALUES (%s, %s, %s) ON CONFLICT (run_id, role) DO UPDATE SET sha256 = EXCLUDED.sha256",
            (run_id, role, artifact.sha256),
        )

    @staticmethod
    def _detail_record(row: tuple[Any, ...]) -> dict[str, Any]:
        payload = row[2] if isinstance(row[2], dict) else {}
        facts = [
            f"{key}: {value}"
            for key, value in payload.items()
            if isinstance(value, (str, int, float, bool))
        ]
        return {
            "sequence": row[0],
            "label": row[1].replace("-", " "),
            "value": " · ".join(facts) if facts else "Observed operational evidence.",
            "occurred_at": row[3].isoformat(),
        }

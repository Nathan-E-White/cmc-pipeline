"""Single-process execution of a small declared runner registry."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Protocol

from app.run_mirror import ArtifactReceipt, PostgresRunMirror, RunAttempt, RunObservation


@dataclass(frozen=True)
class ExecutionRequest:
    run_id: str
    attempt_number: int
    runner_key: str
    container_name: str
    output_directory: Path


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RunnerDefinition:
    service: str
    command: tuple[str, ...]


RUNNERS = {
    "reference-solver": RunnerDefinition(
        "reference-solver", ("verify-case", "--output", "/artifacts")
    ),
}


class Runner(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...


class ArtifactPublisher(Protocol):
    def put_bytes(self, content: bytes, media_type: str) -> ArtifactReceipt: ...


class LocalComposeRunner:
    """Run one declared service under a stable container name; never use caller commands."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        definition = RUNNERS.get(request.runner_key)
        if definition is None:
            raise ValueError(f"Runner {request.runner_key!r} is not declared.")
        request.output_directory.mkdir(parents=True, exist_ok=True)
        command = self._command(request, definition)
        completed: CompletedProcess[str] = run(command, check=False, text=True, capture_output=True)
        if os.environ.get("CMC_EXECUTOR_DOCKER_SOCKET") == "true":
            run(
                [
                    "docker",
                    "cp",
                    f"{request.container_name}:/artifacts/.",
                    str(request.output_directory),
                ],
                check=False,
                text=True,
                capture_output=True,
            )
        return ExecutionResult(completed.returncode, completed.stdout, completed.stderr)

    def container_exists(self, container_name: str) -> bool:
        command = ["docker", "inspect", "--format", "{{.State.Running}}", container_name]
        completed = run(command, check=False, text=True, capture_output=True)
        return completed.returncode == 0 and completed.stdout.strip() == "true"

    @staticmethod
    def _command(request: ExecutionRequest, definition: RunnerDefinition) -> list[str]:
        if os.environ.get("CMC_EXECUTOR_DOCKER_SOCKET") == "true":
            return [
                "docker",
                "run",
                "--name",
                request.container_name,
                f"cmc-pipeline-v3-{definition.service}",
                *definition.command,
            ]
        return [
            "docker",
            "--context",
            "orbstack",
            "compose",
            "run",
            "--name",
            request.container_name,
            "--volume",
            f"{request.output_directory.resolve()}:/artifacts",
            "--entrypoint",
            "/opt/cmc/bin/reference-solver",
            definition.service,
            *definition.command,
        ]


class CaseExecutor:
    """Claims exactly one queued Run Mirror attempt and persists its result."""

    def __init__(
        self,
        runner: Runner,
        mirror: PostgresRunMirror | None = None,
        publisher: ArtifactPublisher | None = None,
    ) -> None:
        self._runner = runner
        self._mirror = mirror
        self._publisher = publisher
        self._active_run_id: str | None = None

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if self._active_run_id is not None:
            raise RuntimeError("The local Case Executor permits one active attempt at a time.")
        self._active_run_id = request.run_id
        try:
            return self._runner.execute(request)
        finally:
            self._active_run_id = None

    def execute_next(self, scratch_root: Path) -> tuple[RunAttempt, ExecutionResult] | None:
        if self._mirror is None:
            raise RuntimeError("execute_next requires a Run Mirror.")
        attempt = self._mirror.claim_next_attempt()
        if attempt is None:
            return None
        request = ExecutionRequest(
            attempt.run_id,
            attempt.attempt_number,
            attempt.runner_key,
            attempt.container_name,
            scratch_root / attempt.run_id / str(attempt.attempt_number),
        )
        try:
            result = self.execute(request)
            artifacts = self._publish_manifest(request.output_directory)
            self._mirror.record(
                attempt.run_id,
                attempt.attempt_number,
                RunObservation(
                    phase_key="verify",
                    event_type="verification-observed",
                    payload={"exit_code": result.exit_code},
                    phase_state="completed" if result.exit_code == 0 else "failed",
                    headline={"exit_code": result.exit_code},
                    trend={},
                    warnings=["Verification completed; no numerical solution outcome is asserted."]
                    if result.exit_code == 0
                    else ["Runner exited nonzero; inspect published artifacts."],
                    artifacts=tuple(artifacts),
                ),
            )
        except Exception as error:
            self._mirror.record(
                attempt.run_id,
                attempt.attempt_number,
                RunObservation(
                    phase_key="verify",
                    event_type="executor-failed",
                    payload={"error": type(error).__name__},
                    phase_state="failed",
                    headline={"text": "Executor could not complete the declared attempt."},
                    trend={},
                    warnings=["Inspect the local executor and published scratch evidence."],
                ),
            )
            self._mirror.finish_attempt(attempt.run_id, attempt.attempt_number, 125)
            raise
        self._mirror.finish_attempt(attempt.run_id, attempt.attempt_number, result.exit_code)
        return attempt, result

    def _publish_manifest(self, output_directory: Path) -> list[tuple[str, ArtifactReceipt]]:
        """Validate a manifest and publish only explicitly declared local files."""
        manifest_path = output_directory / "artifact-manifest.json"
        if self._publisher is None or not manifest_path.is_file():
            return []
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("artifacts") if isinstance(manifest, dict) else None
        if not isinstance(entries, list):
            raise TypeError("artifact-manifest.json must contain an artifacts list.")
        published: list[tuple[str, ArtifactReceipt]] = []
        root = output_directory.resolve()
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("role"), str):
                raise TypeError("Each manifest artifact requires a string role.")
            relative_path, media_type = entry.get("path"), entry.get("media_type")
            if not isinstance(relative_path, str) or not isinstance(media_type, str):
                raise TypeError("Each manifest artifact requires path and media_type strings.")
            source = (root / relative_path).resolve()
            if root not in source.parents or not source.is_file():
                raise ValueError(
                    "Manifest artifact must be a file inside the scoped output directory."
                )
            published.append(
                (entry["role"], self._publisher.put_bytes(source.read_bytes(), media_type))
            )
        return published

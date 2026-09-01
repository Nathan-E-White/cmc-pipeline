"""Serial local execution of declared runners; runners never write operational records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Protocol


@dataclass(frozen=True)
class ExecutionRequest:
    run_id: str
    attempt_number: int
    runner_key: str
    command: tuple[str, ...]
    output_directory: Path


@dataclass(frozen=True)
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str


class Runner(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult: ...


class LocalComposeRunner:
    """The first Runner adapter: one named local container and one scoped output directory."""

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        request.output_directory.mkdir(parents=True, exist_ok=True)
        completed: CompletedProcess[str] = run(
            ["docker", "--context", "orbstack", "compose", "run", "--rm", request.runner_key, *request.command],
            check=False,
            text=True,
            capture_output=True,
        )
        return ExecutionResult(completed.returncode, completed.stdout, completed.stderr)


class CaseExecutor:
    """Serialize a declared attempt and leave numerical interpretation to its runner."""

    def __init__(self, runner: Runner) -> None:
        self._runner = runner
        self._active_run_id: str | None = None

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if self._active_run_id is not None:
            raise RuntimeError("The local Case Executor permits one active attempt at a time.")
        self._active_run_id = request.run_id
        try:
            return self._runner.execute(request)
        finally:
            self._active_run_id = None

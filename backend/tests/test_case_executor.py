from pathlib import Path

import pytest

from app.case_executor import CaseExecutor, ExecutionRequest, ExecutionResult
from app.run_mirror import RunAttempt


class ReentrantRunner:
    def __init__(self) -> None:
        self.executor: CaseExecutor | None = None

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        assert self.executor is not None
        with pytest.raises(RuntimeError, match="one active"):
            self.executor.execute(request)
        return ExecutionResult(0, "", "")


def test_serial_executor_rejects_a_second_attempt_until_the_current_one_finishes(
    tmp_path: Path,
) -> None:
    runner = ReentrantRunner()
    executor = CaseExecutor(runner)
    runner.executor = executor
    request = ExecutionRequest("run-1", 1, "reference-solver", "cmc-v3-run-1-attempt-1", tmp_path)

    assert executor.execute(request).exit_code == 0
    assert executor.execute(request).exit_code == 0


class FakeMirror:
    def __init__(self) -> None:
        self.claimed = False
        self.observations = []
        self.finished = []

    def claim_next_attempt(self):
        if self.claimed:
            return None
        self.claimed = True
        return RunAttempt("run-1", 1, "reference-solver", "cmc-v3-run-1-attempt-1", "running")

    def record(self, run_id, attempt_number, observation) -> None:
        self.observations.append((run_id, attempt_number, observation))

    def finish_attempt(self, run_id, attempt_number, exit_code, **kwargs) -> None:
        self.finished.append((run_id, attempt_number, exit_code, kwargs))


class SuccessfulRunner:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(0, "done", "")


def test_executor_claims_one_declared_attempt_records_observation_and_never_retries(
    tmp_path: Path,
) -> None:
    mirror = FakeMirror()
    executor = CaseExecutor(SuccessfulRunner(), mirror)  # type: ignore[arg-type]

    first = executor.execute_next(tmp_path)

    assert first is not None
    assert first[0].runner_key == "reference-solver"
    assert mirror.observations[0][2].event_type == "verification-observed"
    assert mirror.finished == [
        (
            "run-1",
            1,
            0,
            {"success_outcome": "indeterminate", "evidence_disposition": "indeterminate"},
        )
    ]
    assert executor.execute_next(tmp_path) is None

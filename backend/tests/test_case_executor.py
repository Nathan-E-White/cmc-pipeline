from pathlib import Path

import pytest

from app.case_executor import CaseExecutor, ExecutionRequest, ExecutionResult


class ReentrantRunner:
    def __init__(self) -> None:
        self.executor: CaseExecutor | None = None

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        assert self.executor is not None
        with pytest.raises(RuntimeError, match="one active"):
            self.executor.execute(request)
        return ExecutionResult(0, "", "")


def test_serial_executor_rejects_a_second_attempt_until_the_current_one_finishes(tmp_path: Path) -> None:
    runner = ReentrantRunner()
    executor = CaseExecutor(runner)
    runner.executor = executor
    request = ExecutionRequest("run-1", 1, "reference-solver", ("verify-case",), tmp_path)

    assert executor.execute(request).exit_code == 0
    assert executor.execute(request).exit_code == 0

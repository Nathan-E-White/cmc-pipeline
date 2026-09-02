from pathlib import Path

import h5py
import numpy as np
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
    def __init__(
        self,
        runner_key: str = "r0-reference-field-export/v1",
        workflow_key: str | None = "r0-reference-field-export/v1",
    ) -> None:
        self.claimed = False
        self.runner_key = runner_key
        self.workflow_key = workflow_key
        self.observations = []
        self.finished = []

    def claim_next_attempt(self, run_id=None):
        if self.claimed:
            return None
        self.claimed = True
        card = {"case_id": "r0-elastic-displacement-e200-v1", "workflow_key": self.workflow_key}
        return RunAttempt("run-1", 1, self.runner_key, "cmc-v3-run-1-attempt-1", "running", card)

    def record(self, run_id, attempt_number, observation) -> None:
        self.observations.append((run_id, attempt_number, observation))

    def finish_attempt(self, run_id, attempt_number, exit_code, **kwargs) -> None:
        self.finished.append((run_id, attempt_number, exit_code, kwargs))


class SuccessfulRunner:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(0, "done", "")


class FieldExportRunner:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        request.output_directory.mkdir(parents=True, exist_ok=True)
        (request.output_directory / "field-set.json").write_text(
            """{"version":"cmc.field-set-manifest.v1","field":{"id":"custom","name":"custom","units":"mm","association":"node","components":2,"xdmf_role":"field/custom/xdmf","hdf5_role":"field/custom/hdf5"},"claim_boundary":"Local reference only.","acceptance_role":"field/custom/acceptance","pair_map_role":"field/custom/pair-map"}"""
        )
        (request.output_directory / "acceptance.json").write_text(
            """{"version":"cmc.r0-field-acceptance.v1","status":"accepted","gates":{"mesh_audit":"accepted","solution":"solved"}}"""
        )
        (request.output_directory / "field.xdmf").write_text(
            """<Xdmf><Domain><Grid><Topology TopologyType="Triangle"><DataItem Format="HDF">field.h5:/mesh/cells</DataItem></Topology><Geometry GeometryType="XY"><DataItem Format="HDF">field.h5:/mesh/points</DataItem></Geometry><Attribute Name="custom" AttributeType="Vector" Center="Node"><DataItem Format="HDF">field.h5:/fields/custom</DataItem></Attribute></Grid></Domain></Xdmf>"""
        )
        with h5py.File(request.output_directory / "field.h5", "w") as field:
            field["mesh/cells"] = np.array([[0, 1, 2]], dtype=np.int64)
            field["mesh/points"] = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
            field["fields/custom"] = np.array([[0.0, 0.0], [0.1, 0.0], [0.0, 0.2]])
        (request.output_directory / "artifact-manifest.json").write_text(
            """{"artifacts":[
              {"role":"field-set-manifest","path":"field-set.json","media_type":"application/vnd.cmc.field-set-manifest+json"},
              {"role":"field/custom/xdmf","path":"field.xdmf","media_type":"application/x-xdmf+xml"},
              {"role":"field/custom/hdf5","path":"field.h5","media_type":"application/x-hdf5"},
              {"role":"field/custom/acceptance","path":"acceptance.json","media_type":"application/vnd.cmc.r0-field-acceptance+json"},
              {"role":"field/custom/pair-map","path":"pairs.json","media_type":"application/vnd.cmc.opened-crack-pairs+json"}
            ]}"""
        )
        (request.output_directory / "pairs.json").write_text(
            '{"ordered_element_pairs":[{"id":"pair-1"}]}'
        )
        return ExecutionResult(0, "done", "")


class MemoryPublisher:
    def put_bytes(self, content: bytes, media_type: str):
        from hashlib import sha256

        from app.run_mirror import ArtifactReceipt

        digest = sha256(content).hexdigest()
        return ArtifactReceipt(digest, len(content), media_type, f"sha256/{digest}")


def test_executor_claims_one_declared_attempt_records_observation_and_never_retries(
    tmp_path: Path,
) -> None:
    mirror = FakeMirror()
    executor = CaseExecutor(FieldExportRunner(), mirror, MemoryPublisher())  # type: ignore[arg-type]

    first = executor.execute_next(tmp_path)

    assert first is not None
    assert first[0].runner_key == "r0-reference-field-export/v1"
    assert [item[2].event_type for item in mirror.observations] == [
        "workflow-rendered",
        "stage-started",
        "stage-finished",
        "stage-started",
        "stage-finished",
        "stage-started",
        "stage-finished",
    ]
    assert mirror.finished == [
        (
            "run-1",
            1,
            0,
            {
                "success_outcome": "solved",
                "evidence_disposition": "accepted",
                "phase_key": "publish",
                "success_event_type": "field-export-finished",
                "failure_event_type": "field-export-failed",
                "success_warning": "Accepted local R0 reference field export completed; not physical validation.",
                "failure_warning": "R0 field export failed; published artifacts remain available for review.",
            },
        )
    ]
    assert executor.execute_next(tmp_path) is None


def test_executor_uses_declared_field_export_policy_without_knowing_field_roles(
    tmp_path: Path,
) -> None:
    mirror = FakeMirror()
    executor = CaseExecutor(FieldExportRunner(), mirror, MemoryPublisher())  # type: ignore[arg-type]

    result = executor.execute_next(tmp_path)

    assert result is not None
    assert mirror.observations[-1][2].event_type == "stage-finished"
    assert mirror.finished[0][3] == {
        "success_outcome": "solved",
        "evidence_disposition": "accepted",
        "phase_key": "publish",
        "success_event_type": "field-export-finished",
        "failure_event_type": "field-export-failed",
        "success_warning": "Accepted local R0 reference field export completed; not physical validation.",
        "failure_warning": "R0 field export failed; published artifacts remain available for review.",
    }

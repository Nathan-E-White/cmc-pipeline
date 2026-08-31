"""Focused lifecycle tests for reversible-cohesive convergence orchestration."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/python"))

from converge_reversible_cohesive_edge_crack import (
    ReversibleCohesiveConvergence,
    ReversibleCohesiveToolchain,
)

CARD = {
    "case_id": "edge-cracked-plate-reversible-v2",
    "claim_boundary": "Numerical tracer only; not fracture energy or toughness.",
    "mesh_levels": [
        {"near_tip_mm": 2.0, "far_field_mm": 10.0},
        {"near_tip_mm": 1.0, "far_field_mm": 5.0},
        {"near_tip_mm": 0.5, "far_field_mm": 2.5},
    ],
    "acceptance": {
        "fine_medium_change_percent_max": 2.5,
        "fine_energy_closure_percent_max": 1.0,
    },
}


def _script(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    return path


def _run(statuses: dict[str, str]) -> tuple[dict, Path]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        card = root / "case.json"
        card.write_text(json.dumps(CARD), encoding="utf-8")
        (root / "statuses.json").write_text(json.dumps(statuses), encoding="utf-8")
        generator = _script(
            root / "generator.py",
            """#!/usr/bin/env python3
import pathlib, sys
args=sys.argv; pathlib.Path(args[args.index('--output')+1]).write_text('mesh'); pathlib.Path(args[args.index('--crack-face-pairs-output')+1]).write_text('{}')
""",
        )
        audit = _script(
            root / "audit.py",
            """#!/usr/bin/env python3
import json, pathlib, sys
pathlib.Path(sys.argv[2]).write_text(json.dumps({'mesh': {'kind': 'fixture'}}))
""",
        )
        validator = _script(root / "validator.py", "#!/usr/bin/env python3\n")
        program = _script(
            root / "program.py",
            """#!/usr/bin/env python3
import json, pathlib, sys
args=sys.argv; output=pathlib.Path(args[args.index('--output')+1]); mode=json.loads(pathlib.Path(__file__).with_name('statuses.json').read_text())[output.name]
if mode == 'missing': raise SystemExit(2)
card=json.loads(pathlib.Path(args[args.index('--case-card')+1]).read_text())
increment={'reaction': {'status':'computed','value_mpa_mm':1.0}, 'external_work': {'status':'computed','value_mpa_mm2':1.0}, 'bulk_strain_energy': {'status':'computed','value_mpa_mm2':0.5}, 'reversible_interface_potential_mpa_mm2':0.5, 'mouth_opening_mm':0.1, 'energy_closure': {'status':'computed','mismatch_percent':0.0}, 'j_diagnostic': {'status':'diagnostic-only','contours':[{'radius_mm':1.0,'j_mpa_mm':1.0}]}}
if mode == 'malformed': increment['reaction'] = {'status': 'computed'}
payload={'status':('failed' if mode == 'failed' else 'solved'),'claim_boundary':card['claim_boundary'],'attempts':[],'accepted_increments':([] if mode == 'indeterminate' else [increment])}
output.mkdir(parents=True, exist_ok=True); (output/'reversible-cohesive-program.json').write_text(json.dumps(payload))
""",
        )
        visualizer = _script(
            root / "visualizer.py",
            """#!/usr/bin/env python3
import pathlib, sys
args=sys.argv; pathlib.Path(args[args.index('--output')+1]).write_text('<svg/>')
""",
        )
        output = root / "output"
        payload = ReversibleCohesiveConvergence(
            ReversibleCohesiveToolchain(
                artifact_validator=validator,
                case=root / "case.geo",
                case_card=card,
                generator=generator,
                mesh_audit=audit,
                program_runner=program,
                single_step_solver=root / "solver.py",
                visualizer=visualizer,
            )
        ).run(output)
        # Preserve the observable result after TemporaryDirectory removes the fake tools.
        return payload, output


def test_successful_levels_produce_a_solved_artifact() -> None:
    payload, _ = _run({"coarse": "solved", "medium": "solved", "fine": "solved"})
    assert payload["status"] == "solved"
    assert payload["comparison"]["status"] == "computed"
    assert payload["acceptance"]["status"] == "accepted"


def test_missing_program_artifact_marks_the_level_and_case_failed() -> None:
    payload, _ = _run({"coarse": "solved", "medium": "missing", "fine": "solved"})
    assert payload["status"] == "failed"
    assert payload["levels"][1]["status"] == "failed"
    assert "did not write an artifact" in payload["levels"][1]["program"]["failure"]


def test_incomplete_solved_program_remains_indeterminate() -> None:
    payload, _ = _run({"coarse": "solved", "medium": "indeterminate", "fine": "solved"})
    assert payload["status"] == "indeterminate"
    assert payload["levels"][1]["status"] == "indeterminate"
    assert payload["acceptance"]["status"] == "unavailable"


def test_malformed_solved_metrics_remain_indeterminate() -> None:
    payload, _ = _run({"coarse": "solved", "medium": "malformed", "fine": "solved"})
    assert payload["status"] == "indeterminate"
    assert payload["levels"][1]["status"] == "indeterminate"


def test_runner_reported_failure_marks_the_case_failed() -> None:
    payload, _ = _run({"coarse": "solved", "medium": "failed", "fine": "solved"})
    assert payload["status"] == "failed"
    assert payload["levels"][1]["status"] == "failed"


if __name__ == "__main__":
    test_successful_levels_produce_a_solved_artifact()
    test_missing_program_artifact_marks_the_level_and_case_failed()
    test_incomplete_solved_program_remains_indeterminate()
    test_malformed_solved_metrics_remain_indeterminate()
    test_runner_reported_failure_marks_the_case_failed()

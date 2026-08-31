"""Focused lifecycle tests for reversible-cohesive convergence orchestration."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/python"))

import converge_reversible_cohesive_edge_crack as convergence
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


def _run(
    statuses: dict[str, str], *, tool_failures: dict[str, str] | None = None
) -> tuple[dict, Path]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        card = root / "case.json"
        card.write_text(json.dumps(CARD), encoding="utf-8")
        (root / "statuses.json").write_text(json.dumps(statuses), encoding="utf-8")
        (root / "tool-failures.json").write_text(
            json.dumps(tool_failures or {}), encoding="utf-8"
        )
        generator = _script(
            root / "generator.py",
            """#!/usr/bin/env python3
import json, pathlib, sys
args=sys.argv; output=pathlib.Path(args[args.index('--output')+1]); failures=json.loads(pathlib.Path(__file__).with_name('tool-failures.json').read_text())
if failures.get(output.parent.name) == 'generator': raise SystemExit(2)
output.write_text('mesh'); pathlib.Path(args[args.index('--crack-face-pairs-output')+1]).write_text('{}')
""",
        )
        audit = _script(
            root / "audit.py",
            """#!/usr/bin/env python3
import json, pathlib, sys
mesh=pathlib.Path(sys.argv[1]); failures=json.loads(pathlib.Path(__file__).with_name('tool-failures.json').read_text())
if failures.get(mesh.parent.name) == 'audit': raise SystemExit(2)
pathlib.Path(sys.argv[2]).write_text(json.dumps({'mesh': {'kind': 'fixture'}}))
""",
        )
        validator = _script(
            root / "validator.py",
            """#!/usr/bin/env python3
import json, pathlib, sys
mesh=pathlib.Path(sys.argv[sys.argv.index('--mesh')+1]); failures=json.loads(pathlib.Path(__file__).with_name('tool-failures.json').read_text())
if failures.get(mesh.parent.name) == 'validator': raise SystemExit(2)
""",
        )
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
if mode == 'failed': raise SystemExit(2)
""",
        )
        visualizer = _script(
            root / "visualizer.py",
            """#!/usr/bin/env python3
import json, pathlib, sys
args=sys.argv; mesh=pathlib.Path(args[args.index('--mesh')+1]); failures=json.loads(pathlib.Path(__file__).with_name('tool-failures.json').read_text())
if failures.get(mesh.parent.name) == 'visualizer': raise SystemExit(2)
pathlib.Path(args[args.index('--output')+1]).write_text('<svg/>')
""",
        )
        output = root / "output"
        convergence_run = ReversibleCohesiveConvergence(
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
        )
        if (tool_failures or {}).get("program_runner") == "launch":
            original_run = subprocess.run

            def fail_only_program_runner(command, *args, **kwargs):
                if len(command) > 1 and command[1] == str(program):
                    raise OSError("fixture launch failure")
                return original_run(command, *args, **kwargs)

            with patch.object(
                convergence.subprocess, "run", side_effect=fail_only_program_runner
            ):
                payload = convergence_run.run(output)
        else:
            payload = convergence_run.run(output)
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


def test_tool_failure_marks_only_its_level_and_later_levels_still_run() -> None:
    payload, _ = _run(
        {"coarse": "solved", "medium": "solved", "fine": "solved"},
        tool_failures={"coarse": "generator"},
    )
    assert payload["status"] == "failed"
    assert [level["status"] for level in payload["levels"]] == [
        "failed",
        "solved",
        "solved",
    ]
    assert payload["comparison"]["status"] == "unavailable"


def test_visualizer_failure_preserves_numerical_evidence() -> None:
    payload, _ = _run(
        {"coarse": "solved", "medium": "solved", "fine": "solved"},
        tool_failures={"medium": "visualizer"},
    )
    assert payload["status"] == "solved"
    assert payload["comparison"]["status"] == "computed"
    assert payload["artifacts"]["case_visual"]["status"] == "failed"


def test_failed_total_artifact_remains_contract_valid() -> None:
    payload, _ = _run(
        {"coarse": "solved", "medium": "solved", "fine": "solved"},
        tool_failures={"coarse": "generator"},
    )
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", encoding="utf-8"
    ) as artifact:
        json.dump(payload, artifact)
        artifact.flush()
        subprocess.run(
            [
                sys.executable,
                str(
                    ROOT
                    / "reference/tests/validate_reversible_cohesive_convergence_artifact.py"
                ),
                artifact.name,
            ],
            check=True,
        )


def test_program_runner_launch_failure_is_declared_for_every_level() -> None:
    payload, _ = _run(
        {"coarse": "solved", "medium": "solved", "fine": "solved"},
        tool_failures={"program_runner": "launch"},
    )
    assert payload["status"] == "failed"
    assert [level["program"]["claim_boundary"] for level in payload["levels"]] == [
        CARD["claim_boundary"],
        CARD["claim_boundary"],
        CARD["claim_boundary"],
    ]


if __name__ == "__main__":
    test_successful_levels_produce_a_solved_artifact()
    test_missing_program_artifact_marks_the_level_and_case_failed()
    test_incomplete_solved_program_remains_indeterminate()
    test_malformed_solved_metrics_remain_indeterminate()
    test_runner_reported_failure_marks_the_case_failed()
    test_tool_failure_marks_only_its_level_and_later_levels_still_run()
    test_visualizer_failure_preserves_numerical_evidence()
    test_failed_total_artifact_remains_contract_valid()
    test_program_runner_launch_failure_is_declared_for_every_level()

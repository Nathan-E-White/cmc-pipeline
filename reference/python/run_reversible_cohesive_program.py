#!/usr/bin/env python3
"""Run Item 5's monotonic program through the one-step PETSc adapter."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from monotonic_displacement_program import MonotonicDisplacementProgram, SingleDisplacementResult


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--crack-face-pairs", type=Path, required=True)
    parser.add_argument("--case-card", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    card = json.loads(args.case_card.read_text(encoding="utf-8"))
    program = MonotonicDisplacementProgram.from_case_card(card)
    attempts_root = args.output / "single-step-attempts"
    counter = 0

    def solve(displacement_mm: float) -> SingleDisplacementResult:
        nonlocal counter
        counter += 1
        directory = attempts_root / f"{counter:04d}"
        command = [sys.executable, str(args.solver), "--mesh", str(args.mesh), "--crack-face-pairs", str(args.crack_face_pairs),
                   "--case-card", str(args.case_card), "--top-displacement-mm", repr(displacement_mm), "--output", str(directory)]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        result_path = directory / "reversible-cohesive-step.json"
        if completed.returncode != 0 or not result_path.is_file():
            return SingleDisplacementResult(False, failure=(completed.stderr.strip() or completed.stdout.strip() or "single-step solver failed"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
        return SingleDisplacementResult(
            True, mouth_opening_mm=result["mouth_opening_mm"], newton_iterations=result["newton_iterations"],
            relative_residual=result["relative_residual"], residual_history=tuple(result["residual_history"]),
            reversible_interface_potential_mpa_mm2=result["reversible_interface_potential_mpa_mm2"],
            diagnostics=result["diagnostics"],
        )

    artifact = program.run(solve)
    args.output.mkdir(parents=True, exist_ok=True)
    artifact.update({"case_id": card["case_id"], "claim_boundary": card["claim_boundary"]})
    (args.output / "reversible-cohesive-program.json").write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if artifact["status"] != "solved":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run Item 5's monotonic program through the one-step PETSc adapter."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from monotonic_displacement_program import MonotonicDisplacementProgram
from single_displacement_execution import SingleDisplacementExecution


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
    execution = SingleDisplacementExecution(
        attempts_root=args.output / "single-step-attempts",
        case_card=args.case_card,
        crack_face_pairs=args.crack_face_pairs,
        mesh=args.mesh,
        solver=args.solver,
    )
    artifact = program.run(execution.solve)
    args.output.mkdir(parents=True, exist_ok=True)
    artifact.update({"case_id": card["case_id"], "claim_boundary": card["claim_boundary"]})
    (args.output / "reversible-cohesive-program.json").write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if artifact["status"] != "solved":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

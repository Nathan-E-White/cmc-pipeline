"""Execute and decode one declared reversible-cohesive displacement attempt."""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from monotonic_displacement_program import SingleDisplacementResult


class SingleDisplacementExecution:
    """Own process evidence and decoding behind the one-step solver seam."""

    def __init__(
        self,
        *,
        attempts_root: Path,
        case_card: Path,
        crack_face_pairs: Path,
        mesh: Path,
        solver: Path,
    ) -> None:
        self._attempts_root = attempts_root
        self._case_card = case_card
        self._crack_face_pairs = crack_face_pairs
        self._mesh = mesh
        self._solver = solver
        self._counter = 0

    def solve(self, displacement_mm: float) -> SingleDisplacementResult:
        self._counter += 1
        directory = self._attempts_root / f"{self._counter:04d}"
        directory.mkdir(parents=True, exist_ok=True)
        command = [
            sys.executable,
            str(self._solver),
            "--mesh",
            str(self._mesh),
            "--crack-face-pairs",
            str(self._crack_face_pairs),
            "--case-card",
            str(self._case_card),
            "--top-displacement-mm",
            repr(displacement_mm),
            "--output",
            str(directory),
        ]
        try:
            completed = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
        except OSError as error:
            return SingleDisplacementResult(
                False, failure=f"single-step solver could not start: {error}"
            )
        result_path = directory / "reversible-cohesive-step.json"
        if completed.returncode != 0 or not result_path.is_file():
            detail = completed.stderr.strip() or completed.stdout.strip()
            return SingleDisplacementResult(
                False,
                failure=detail or "single-step solver did not write an artifact",
            )
        try:
            result = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return SingleDisplacementResult(
                False, failure="single-step solver wrote malformed JSON evidence"
            )
        if not isinstance(result, Mapping):
            return SingleDisplacementResult(
                False, failure="single-step solver result must be a JSON object"
            )
        try:
            diagnostics = result["diagnostics"]
            if not isinstance(diagnostics, Mapping):
                raise TypeError("diagnostics is not an object")
            return SingleDisplacementResult(
                True,
                mouth_opening_mm=result["mouth_opening_mm"],
                newton_iterations=result["newton_iterations"],
                relative_residual=result["relative_residual"],
                residual_history=tuple(result["residual_history"]),
                reversible_interface_potential_mpa_mm2=result[
                    "reversible_interface_potential_mpa_mm2"
                ],
                diagnostics=diagnostics,
            )
        except (KeyError, TypeError):
            return SingleDisplacementResult(
                False, failure="single-step solver result is missing required evidence"
            )

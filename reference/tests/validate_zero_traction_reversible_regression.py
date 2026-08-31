#!/usr/bin/env python3
"""Regression-check the test-only zero-traction adapter against linear evidence.

The adapter is constructed here, outside the public solver command.  With its
zero residual and tangent the reversible-step adapter reduces to the declared
plain displacement-controlled linear-elastic problem.  The fixed values below
are the independently retained medium-mesh linear baseline for this pinned
image and mesh generator.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path("/opt/cmc")
sys.path.insert(0, str(ROOT / "python"))

from bilinear_mode_i_opening_law import OpeningLawResponse  # noqa: E402
import paired_lip_assembler as paired_lip  # noqa: E402
import solve_reversible_cohesive_edge_crack as solver  # noqa: E402


class ZeroTractionLaw:
    """Test-only adapter at the internal normal-opening-law seam."""

    peak_opening_mm = 0.01
    final_opening_mm = 0.1

    @staticmethod
    def evaluate(_opening_mm: float) -> OpeningLawResponse:
        return OpeningLawResponse(traction_mpa=0.0, tangent_mpa_per_mm=0.0, reversible_potential_mpa_mm=0.0)


class UnconstrainedZeroTractionAssembler(paired_lip.PairedLipAssembler):
    """No feasibility limit is needed when the test adapter has no interface law."""

    def maximum_feasible_step(self, *_args) -> float:
        return 1.0


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        mesh = output / "medium.msh"
        pairs = output / "pairs.json"
        subprocess.run([
            "python3", str(ROOT / "python/generate_edge_crack_mesh.py"),
            "--case", str(ROOT / "cases/edge-cracked-plate-v1.geo"),
            "--output", str(mesh), "--near-size", "1", "--far-size", "5",
            "--crack-face-pairs-output", str(pairs),
        ], check=True)
        original_assembler, original_law, original_argv = solver.PairedLipAssembler, solver.BilinearModeIOpeningLaw, sys.argv
        try:
            solver.PairedLipAssembler = UnconstrainedZeroTractionAssembler
            solver.BilinearModeIOpeningLaw = lambda *_args: ZeroTractionLaw()
            sys.argv = [
                "solve", "--mesh", str(mesh), "--crack-face-pairs", str(pairs),
                "--case-card", str(ROOT / "cases/edge-cracked-plate-reversible-v2.json"),
                "--top-displacement-mm", "0.001", "--output", str(output / "result"),
            ]
            solver.main()
        finally:
            solver.PairedLipAssembler, solver.BilinearModeIOpeningLaw, sys.argv = original_assembler, original_law, original_argv
        result = json.loads((output / "result/reversible-cohesive-step.json").read_text(encoding="utf-8"))
        baseline = {
            "reaction_mpa_mm": 92.67256052085862,
            "mouth_opening_mm": 0.00037593105278687093,
            "bulk_strain_energy_mpa_mm2": 0.04633741696660265,
        }
        assert result["newton_iterations"] == 1
        assert math.isclose(result["mouth_opening_mm"], baseline["mouth_opening_mm"], rel_tol=1e-10)
        assert math.isclose(result["diagnostics"]["reaction"]["value_mpa_mm"], baseline["reaction_mpa_mm"], rel_tol=1e-10)
        assert math.isclose(result["diagnostics"]["bulk_strain_energy"]["value_mpa_mm2"], baseline["bulk_strain_energy_mpa_mm2"], rel_tol=1e-10)
        assert result["reversible_interface_potential_mpa_mm2"] == 0.0


if __name__ == "__main__":
    main()

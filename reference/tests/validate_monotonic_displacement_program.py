#!/usr/bin/env python3
"""Contract tests for the bounded monotonic displacement program."""
from __future__ import annotations

import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/python"))

from monotonic_displacement_program import MonotonicDisplacementProgram, SingleDisplacementResult  # noqa: E402


def _program(**overrides) -> MonotonicDisplacementProgram:
    values = dict(initial_increment_mm=0.4, maximum_displacement_mm=2.0, mouth_opening_target_mm=0.1,
                  relative_endpoint_tolerance=1e-4, relative_residual_max=1e-8, iterations_max=25,
                  cutback_factor=0.5, consecutive_cutbacks_max=8, normalized_increment_min=1e-4)
    values.update(overrides)
    return MonotonicDisplacementProgram(**values)


def _solved(displacement: float) -> SingleDisplacementResult:
    return SingleDisplacementResult(True, mouth_opening_mm=displacement / 10.0, newton_iterations=3,
                                   relative_residual=1e-10, residual_history=(1.0, 1e-10),
                                   reversible_interface_potential_mpa_mm2=displacement)


def test_brackets_and_bisects_the_mouth_event_with_increment_evidence() -> None:
    artifact = _program().run(_solved)
    assert artifact["status"] == "solved"
    final = artifact["accepted_increments"][-1]
    assert final["phase"] == "endpoint-bisection"
    assert abs(final["mouth_opening_mm"] - 0.1) <= 1e-5
    assert {"load_factor", "residual_history", "reversible_interface_potential_mpa_mm2"} <= set(final)


def test_failed_steps_are_recorded_then_cut_back_without_mutating_the_solver_contract() -> None:
    calls: list[float] = []
    def solve(displacement: float) -> SingleDisplacementResult:
        calls.append(displacement)
        if displacement > 0.25:
            return SingleDisplacementResult(False, failure="Newton divergence", residual_history=(1.0, 0.4))
        return _solved(displacement)
    artifact = _program(initial_increment_mm=0.4, maximum_displacement_mm=1.0).run(solve)
    assert artifact["attempts"][0]["accepted"] is False
    assert artifact["attempts"][0]["failure"] == "Newton divergence"
    assert 0.2 in calls


def test_kill_switch_emits_an_explicit_failed_artifact() -> None:
    failed = lambda _: SingleDisplacementResult(False, failure="iteration cap", residual_history=(1.0,))
    artifact = _program(initial_increment_mm=0.4, normalized_increment_min=0.15).run(failed)
    assert artifact["status"] == "failed"
    assert artifact["failure"] == "nonlinear cutback kill switch"
    assert artifact["attempts"][-1]["accepted"] is False


def test_rejects_a_step_that_claims_success_without_the_declared_residual_limit() -> None:
    artifact = _program(normalized_increment_min=0.15).run(
        lambda _: SingleDisplacementResult(True, mouth_opening_mm=0.01, newton_iterations=3, relative_residual=1e-4)
    )
    assert artifact["status"] == "failed"
    assert "single-step solver did not converge" in artifact["attempts"][0]["failure"]


def test_case_card_constructs_the_declared_program() -> None:
    card = json.loads((ROOT / "reference/cases/edge-cracked-plate-reversible-v2.json").read_text(encoding="utf-8"))
    program = MonotonicDisplacementProgram.from_case_card(card)
    assert program.initial_increment_mm == 0.001
    assert program.maximum_displacement_mm == 1.0


def test_program_owns_reaction_work_and_final_energy_closure() -> None:
    def solve(displacement: float) -> SingleDisplacementResult:
        return SingleDisplacementResult(
            True, mouth_opening_mm=displacement / 10.0, newton_iterations=2, relative_residual=1e-10,
            reversible_interface_potential_mpa_mm2=0.25 * displacement,
            diagnostics={"reaction": {"status": "computed", "value_mpa_mm": displacement},
                         "bulk_strain_energy": {"status": "computed", "value_mpa_mm2": 0.25 * displacement}},
        )
    artifact = _program().run(solve)
    final = artifact["accepted_increments"][-1]
    assert final["external_work"]["status"] == "computed"
    assert final["energy_closure"]["status"] == "computed"
    assert final["energy_closure"]["mismatch_percent"] == 0.0


if __name__ == "__main__":
    test_brackets_and_bisects_the_mouth_event_with_increment_evidence()
    test_failed_steps_are_recorded_then_cut_back_without_mutating_the_solver_contract()
    test_kill_switch_emits_an_explicit_failed_artifact()
    test_rejects_a_step_that_claims_success_without_the_declared_residual_limit()
    test_case_card_constructs_the_declared_program()
    test_program_owns_reaction_work_and_final_energy_closure()

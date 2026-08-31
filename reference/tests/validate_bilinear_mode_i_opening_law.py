#!/usr/bin/env python3
"""Public-contract tests for the history-free bilinear Mode-I opening law."""

from __future__ import annotations

import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/python"))

from bilinear_mode_i_opening_law import (  # noqa: E402
    BilinearModeIOpeningLaw,
    OpeningLawError,
)


def _law() -> BilinearModeIOpeningLaw:
    return BilinearModeIOpeningLaw(
        peak_traction_mpa=20.0,
        peak_opening_mm=0.01,
        final_opening_mm=0.1,
    )


def test_elastic_branch_returns_traction_tangent_and_reversible_potential() -> None:
    response = _law().evaluate(0.005)
    assert math.isclose(response.traction_mpa, 10.0)
    assert math.isclose(response.tangent_mpa_per_mm, 2_000.0)
    assert math.isclose(response.reversible_potential_mpa_mm, 0.025)


def test_peak_kink_is_continuous_and_uses_the_elastic_branch_tangent() -> None:
    response = _law().evaluate(0.01)
    assert math.isclose(response.traction_mpa, 20.0)
    assert math.isclose(response.tangent_mpa_per_mm, 2_000.0)
    assert math.isclose(response.reversible_potential_mpa_mm, 0.1)


def test_softening_branch_returns_the_declared_negative_tangent_and_potential() -> None:
    response = _law().evaluate(0.055)
    assert math.isclose(response.traction_mpa, 10.0)
    assert math.isclose(response.tangent_mpa_per_mm, -20.0 / 0.09)
    assert math.isclose(response.reversible_potential_mpa_mm, 0.775)


def test_final_opening_kink_and_larger_openings_have_zero_traction() -> None:
    law = _law()
    at_final = law.evaluate(0.1)
    beyond_final = law.evaluate(0.2)
    for response in (at_final, beyond_final):
        assert math.isclose(response.traction_mpa, 0.0)
        assert math.isclose(response.tangent_mpa_per_mm, 0.0)
        assert math.isclose(response.reversible_potential_mpa_mm, 1.0)


def test_rejects_invalid_parameter_ordering_and_negative_opening() -> None:
    for parameters in (
        {"peak_traction_mpa": 0.0, "peak_opening_mm": 0.01, "final_opening_mm": 0.1},
        {"peak_traction_mpa": 20.0, "peak_opening_mm": 0.0, "final_opening_mm": 0.1},
        {"peak_traction_mpa": 20.0, "peak_opening_mm": 0.1, "final_opening_mm": 0.1},
    ):
        try:
            BilinearModeIOpeningLaw(**parameters)
        except OpeningLawError:
            pass
        else:
            raise AssertionError("invalid law parameters must be rejected")

    try:
        _law().evaluate(-1e-12)
    except OpeningLawError:
        pass
    else:
        raise AssertionError("negative opening must be rejected")


if __name__ == "__main__":
    test_elastic_branch_returns_traction_tangent_and_reversible_potential()
    test_peak_kink_is_continuous_and_uses_the_elastic_branch_tangent()
    test_softening_branch_returns_the_declared_negative_tangent_and_potential()
    test_final_opening_kink_and_larger_openings_have_zero_traction()
    test_rejects_invalid_parameter_ordering_and_negative_opening()

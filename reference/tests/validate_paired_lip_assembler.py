#!/usr/bin/env python3
"""Public patch tests for the declared quadratic paired-lip assembler."""

from __future__ import annotations

import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reference/python"))

from bilinear_mode_i_opening_law import BilinearModeIOpeningLaw  # noqa: E402
from paired_lip_assembler import PairedLipAssembler, PairedLipAssemblyError  # noqa: E402


def _pair(nodes_offset: int = 0) -> dict:
    return {
        "reference_interval_mm": [0.0, 1.0],
        "minus": {"node_ids": [1 + nodes_offset, 2 + nodes_offset, 3 + nodes_offset], "reference_coordinates_mm": [0.0, 1.0, 0.5]},
        "plus": {"node_ids": [11 + nodes_offset, 12 + nodes_offset, 13 + nodes_offset], "reference_coordinates_mm": [0.0, 1.0, 0.5]},
    }


def _map(*pairs: dict) -> dict:
    return {"reference_trace": {"normal_minus_to_plus": [0.0, 1.0]}, "ordered_element_pairs": list(pairs)}


def _law() -> BilinearModeIOpeningLaw:
    return BilinearModeIOpeningLaw(peak_traction_mpa=20.0, peak_opening_mm=0.01, final_opening_mm=0.1)


def _uniform(opening: float, pair: dict) -> dict[int, tuple[float, float]]:
    values = {node: (0.0, 0.0) for node in pair["minus"]["node_ids"]}
    values.update({node: (0.0, opening) for node in pair["plus"]["node_ids"]})
    return values


def _resultant(contribution, nodes: list[int]) -> tuple[float, float]:
    return tuple(sum(contribution.residual_by_node[node][axis] for node in nodes) for axis in range(2))


def test_uniform_opening_has_equal_and_opposite_resultants_and_consistent_tangent() -> None:
    pair = _pair()
    assembler = PairedLipAssembler.from_pair_map(_law(), _map(pair))
    contribution = assembler.assemble(_map(pair), _uniform(0.005, pair))
    minus = _resultant(contribution, pair["minus"]["node_ids"])
    plus = _resultant(contribution, pair["plus"]["node_ids"])
    assert math.isclose(minus[0], 0.0, abs_tol=1e-12)
    assert math.isclose(plus[0], 0.0, abs_tol=1e-12)
    assert math.isclose(minus[1], -10.0, abs_tol=1e-12)
    assert math.isclose(plus[1], 10.0, abs_tol=1e-12)
    assert math.isclose(minus[1] + plus[1], 0.0, abs_tol=1e-12)
    tangent_sum = sum(contribution.tangent_by_node_pair[(i, j)][1][1] for i in pair["plus"]["node_ids"] for j in pair["plus"]["node_ids"])
    assert math.isclose(tangent_sum, 2_000.0, abs_tol=1e-10)


def test_rigid_translation_and_rotation_have_zero_opening() -> None:
    pair = _pair()
    values: dict[int, tuple[float, float]] = {}
    for side in ("minus", "plus"):
        for node, x in zip(pair[side]["node_ids"], pair[side]["reference_coordinates_mm"], strict=True):
            values[node] = (4.0 - 0.3 * 100.0, -2.0 + 0.3 * x)
    contribution = PairedLipAssembler.from_pair_map(_law(), _map(pair)).assemble(_map(pair), values)
    assert all(math.isclose(component, 0.0, abs_tol=1e-12) for value in contribution.residual_by_node.values() for component in value)


def test_pair_enumeration_is_invariant() -> None:
    first, second = _pair(), _pair(100)
    values = _uniform(0.005, first) | _uniform(0.02, second)
    assembler = PairedLipAssembler.from_pair_map(_law(), _map(first, second))
    forward = assembler.assemble(_map(first, second), values)
    reverse = assembler.assemble(_map(second, first), values)
    assert forward.residual_by_node == reverse.residual_by_node
    assert forward.tangent_by_node_pair == reverse.tangent_by_node_pair
    assert math.isclose(forward.reversible_potential_mpa_mm2, reverse.reversible_potential_mpa_mm2)


def test_breakpoint_subdivision_finds_one_and_both_law_kinks() -> None:
    pair = _pair()
    assembler = PairedLipAssembler.from_pair_map(_law(), _map(pair))
    one = _uniform(0.0, pair)
    one[11], one[12], one[13] = (0.0, 0.0), (0.0, 0.02), (0.0, 0.01)
    assert assembler.assemble(_map(pair), one).quadrature_subintervals == 2
    both = _uniform(0.0, pair)
    both[11], both[12], both[13] = (0.0, 0.0), (0.0, 0.12), (0.0, 0.06)
    assert assembler.assemble(_map(pair), both).quadrature_subintervals == 3


def test_negative_opening_at_quadrature_is_rejected() -> None:
    pair = _pair()
    try:
        PairedLipAssembler.from_pair_map(_law(), _map(pair)).assemble(_map(pair), _uniform(-1e-4, pair))
    except PairedLipAssemblyError as error:
        assert "negative opening" in str(error)
    else:
        raise AssertionError("negative opening must fail this no-contact tracer")


if __name__ == "__main__":
    test_uniform_opening_has_equal_and_opposite_resultants_and_consistent_tangent()
    test_rigid_translation_and_rotation_have_zero_opening()
    test_pair_enumeration_is_invariant()
    test_breakpoint_subdivision_finds_one_and_both_law_kinks()
    test_negative_opening_at_quadrature_is_rejected()

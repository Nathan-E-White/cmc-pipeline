#!/usr/bin/env python3
"""Validate the declared input contract for the reversible cohesive tracer."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


EXPECTED_EXCLUSIONS = [
    "contact",
    "compression",
    "friction",
    "irreversible-damage",
    "crack-advance",
    "fibre-interface-resolution",
    "calibrated-material-property-claim",
    "toughness-or-fracture-energy-claim",
]


class ContractError(ValueError):
    """The supplied case card does not declare this bounded tracer."""


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be an object")
    return value


def _required(mapping: dict[str, Any], name: str, *keys: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise ContractError(f"{name} is missing required field(s): {', '.join(missing)}")


def _equal(value: Any, expected: Any, name: str) -> None:
    if value != expected:
        raise ContractError(f"{name} must be {expected!r}")


def _number(value: Any, expected: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContractError(f"{name} must be numeric")
    if not math.isfinite(value) or not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-12):
        raise ContractError(f"{name} must be {expected}")


def validate_case_card(card: Any) -> None:
    """Validate every Step 1 input and boundary required by the approved plan."""
    root = _mapping(card, "case card")
    _required(
        root,
        "case card",
        "case_id",
        "status",
        "geometry",
        "model",
        "loading",
        "fracture_quantity",
        "declared_exclusions",
        "claim_boundary",
    )
    _equal(root["case_id"], "edge-cracked-plate-reversible-v2", "case_id")
    _equal(
        root["status"],
        "plane-strain-fixed-crack-reversible-cohesive-tracer",
        "status",
    )

    geometry = _mapping(root["geometry"], "geometry")
    _required(geometry, "geometry", "width_mm", "height_mm", "crack_length_mm", "crack_y_mm")
    for key, expected in (("width_mm", 100.0), ("height_mm", 200.0), ("crack_length_mm", 30.0), ("crack_y_mm", 100.0)):
        _number(geometry[key], expected, f"geometry.{key}")

    model = _mapping(root["model"], "model")
    _required(
        model,
        "model",
        "assumption",
        "youngs_modulus_gpa",
        "poissons_ratio",
        "crack_growth",
        "cohesive_interface",
    )
    _equal(model["assumption"], "plane_strain", "model.assumption")
    _number(model["youngs_modulus_gpa"], 200.0, "model.youngs_modulus_gpa")
    _number(model["poissons_ratio"], 0.3, "model.poissons_ratio")
    _equal(model["crack_growth"], "fixed", "model.crack_growth")

    interface = _mapping(model["cohesive_interface"], "model.cohesive_interface")
    _required(interface, "model.cohesive_interface", "kind", "opening_definition", "normal_convention", "law", "provenance")
    _equal(interface["kind"], "reversible-bilinear-mode-i-opening", "model.cohesive_interface.kind")
    _equal(interface["opening_definition"], "dot(u_plus-u_minus, normal_minus_to_plus)", "model.cohesive_interface.opening_definition")
    _equal(interface["normal_convention"], "minus-lip-to-plus-lip", "model.cohesive_interface.normal_convention")

    law = _mapping(interface["law"], "model.cohesive_interface.law")
    _required(law, "model.cohesive_interface.law", "peak_traction_mpa", "peak_opening_mm", "final_opening_mm", "initial_tangent_mpa_per_mm", "reported_quantity")
    _number(law["peak_traction_mpa"], 20.0, "model.cohesive_interface.law.peak_traction_mpa")
    _number(law["peak_opening_mm"], 0.01, "model.cohesive_interface.law.peak_opening_mm")
    _number(law["final_opening_mm"], 0.1, "model.cohesive_interface.law.final_opening_mm")
    _number(law["initial_tangent_mpa_per_mm"], 2_000.0, "model.cohesive_interface.law.initial_tangent_mpa_per_mm")
    _equal(law["reported_quantity"], "reversible-interface-potential", "model.cohesive_interface.law.reported_quantity")

    provenance = _mapping(interface["provenance"], "model.cohesive_interface.provenance")
    _required(provenance, "model.cohesive_interface.provenance", "authority", "non_calibrated")
    _equal(provenance["authority"], "synthetic", "model.cohesive_interface.provenance.authority")
    _equal(provenance["non_calibrated"], True, "model.cohesive_interface.provenance.non_calibrated")

    loading = _mapping(root["loading"], "loading")
    _required(loading, "loading", "kind", "program")
    _equal(loading["kind"], "monotonic-top-boundary-displacement", "loading.kind")
    program = _mapping(loading["program"], "loading.program")
    _required(program, "loading.program", "boundary", "endpoint", "newton")
    _equal(program["boundary"], "loaded", "loading.program.boundary")
    endpoint = _mapping(program["endpoint"], "loading.program.endpoint")
    _required(endpoint, "loading.program.endpoint", "quantity", "mouth_opening_mm", "relative_tolerance", "crossing_policy")
    _equal(endpoint["quantity"], "mouth-opening", "loading.program.endpoint.quantity")
    _number(endpoint["mouth_opening_mm"], 0.1, "loading.program.endpoint.mouth_opening_mm")
    _number(endpoint["relative_tolerance"], 1e-4, "loading.program.endpoint.relative_tolerance")
    _equal(endpoint["crossing_policy"], "bracket-and-bisect-final-displacement", "loading.program.endpoint.crossing_policy")
    newton = _mapping(program["newton"], "loading.program.newton")
    _required(newton, "loading.program.newton", "relative_residual_max", "iterations_max", "cutback_factor", "consecutive_cutbacks_max", "normalized_increment_min")
    _number(newton["relative_residual_max"], 1e-8, "loading.program.newton.relative_residual_max")
    _number(newton["iterations_max"], 25.0, "loading.program.newton.iterations_max")
    _number(newton["cutback_factor"], 0.5, "loading.program.newton.cutback_factor")
    _number(newton["consecutive_cutbacks_max"], 8.0, "loading.program.newton.consecutive_cutbacks_max")
    _number(newton["normalized_increment_min"], 1e-4, "loading.program.newton.normalized_increment_min")

    fracture_quantity = _mapping(root["fracture_quantity"], "fracture_quantity")
    _required(fracture_quantity, "fracture_quantity", "method", "contour_radii_mm")
    _equal(fracture_quantity["method"], "domain-integral-diagnostic", "fracture_quantity.method")
    _equal(fracture_quantity["contour_radii_mm"], [8, 12], "fracture_quantity.contour_radii_mm")
    _equal(root["declared_exclusions"], EXPECTED_EXCLUSIONS, "declared_exclusions")
    if not isinstance(root["claim_boundary"], str) or "not fracture energy or toughness" not in root["claim_boundary"]:
        raise ContractError("claim_boundary must exclude fracture-energy and toughness claims")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-card", type=Path, required=True)
    args = parser.parse_args()
    try:
        card = json.loads(args.case_card.read_text(encoding="utf-8"))
        validate_case_card(card)
    except (OSError, json.JSONDecodeError, ContractError) as error:
        print(f"reversible case contract error: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    main()

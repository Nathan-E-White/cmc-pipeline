#!/usr/bin/env python3
"""Reject malformed Item 6 reversible-cohesive convergence evidence."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    errors = []
    if payload.get("case_id") != "edge-cracked-plate-reversible-v2": errors.append("wrong case")
    if payload.get("status") not in {"solved", "failed", "indeterminate"}: errors.append("invalid status")
    if "analytical_authority" in payload: errors.append("reversible tracer must not claim analytical authority")
    if "not fracture energy or toughness" not in payload.get("claim_boundary", ""): errors.append("missing claim boundary")
    adjudication = payload.get("adjudication", "")
    if "J is diagnostic only" not in adjudication or "toughness or fracture-energy authority" not in adjudication:
        errors.append("missing J claim boundary")
    levels = payload.get("levels", [])
    if [item.get("name") for item in levels] != ["coarse", "medium", "fine"]: errors.append("wrong mesh levels")
    for level in levels:
        if level.get("status") not in {"solved", "failed", "indeterminate"}: errors.append("invalid level status")
        program = level.get("program", {})
        if not isinstance(program.get("attempts"), list): errors.append("attempt history missing")
        if program.get("claim_boundary") != payload.get("claim_boundary"): errors.append("program claim boundary mismatch")
        metrics = level.get("metrics")
        if metrics is not None:
            if metrics.get("j_diagnostic", {}).get("status") != "diagnostic-only": errors.append("J must remain diagnostic-only")
            if metrics.get("energy_closure", {}).get("status") != "computed": errors.append("solved metrics missing energy closure")
    if payload.get("status") == "solved":
        comparison = payload.get("comparison", {})
        if comparison.get("status") != "computed": errors.append("missing solved comparison")
        if comparison.get("energy_closure", {}).get("status") != "computed": errors.append("missing energy closure")
    acceptance = payload.get("acceptance", {})
    if acceptance.get("status") not in {"accepted", "rejected", "unavailable"}:
        errors.append("invalid acceptance status")
    gates = acceptance.get("gates", {})
    if gates.get("fine_medium_change_percent_max") != 2.5:
        errors.append("missing refinement acceptance gate")
    if gates.get("fine_energy_closure_percent_max") != 1.0:
        errors.append("missing energy acceptance gate")
    if payload.get("status") == "solved" and acceptance.get("status") == "unavailable":
        errors.append("solved artifact has no acceptance adjudication")
    if acceptance.get("status") in {"accepted", "rejected"}:
        observed = acceptance.get("observed", {})
        if not isinstance(observed.get("fine_medium_change_percent"), dict): errors.append("missing observed refinement evidence")
        if not isinstance(observed.get("fine_energy_closure_percent"), (int, float)): errors.append("missing observed energy evidence")
    if errors: raise SystemExit("; ".join(errors))


if __name__ == "__main__":
    main()

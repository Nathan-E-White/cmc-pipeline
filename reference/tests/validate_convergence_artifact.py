#!/usr/bin/env python3
"""Check the public convergence artifact without recomputing its benchmark."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def validate(payload: dict) -> list[str]:
    errors = []
    if payload.get("case_id") != "edge-cracked-plate-v1": errors.append("wrong case")
    if payload.get("status") != "accepted": errors.append("not accepted")
    if payload.get("analytical_authority", {}).get("plane_strain_j_mpa_mm") != 11.815615: errors.append("wrong NASA benchmark")
    levels = payload.get("levels", [])
    if [level.get("name") for level in levels] != ["coarse", "medium", "fine"]: errors.append("missing declared levels")
    for level in levels:
        if len(level.get("contours", [])) != 2: errors.append(f"bad contours for {level.get('name')}")
        if level.get("mesh", {}).get("minimum_quality", 0) < 0.2: errors.append(f"bad mesh for {level.get('name')}")
    comparison, gates = payload.get("comparison", {}), payload.get("gates", {})
    if comparison.get("fine_analytical_error_percent", float("inf")) > gates.get("analytical_error_percent_max", 0): errors.append("analytical gate")
    if comparison.get("fine_medium_change_percent", float("inf")) > gates.get("fine_medium_change_percent_max", 0): errors.append("mesh-change gate")
    return errors


if __name__ == "__main__":
    problems = validate(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    if problems:
        print("; ".join(problems), file=sys.stderr)
        raise SystemExit(1)

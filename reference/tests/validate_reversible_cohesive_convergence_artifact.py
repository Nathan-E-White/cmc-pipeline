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
    levels = payload.get("levels", [])
    if [item.get("name") for item in levels] != ["coarse", "medium", "fine"]: errors.append("wrong mesh levels")
    for level in levels:
        if level.get("status") not in {"solved", "failed", "indeterminate"}: errors.append("invalid level status")
        if not isinstance(level.get("program", {}).get("attempts"), list): errors.append("attempt history missing")
    if payload.get("status") == "solved":
        comparison = payload.get("comparison", {})
        if comparison.get("status") != "computed": errors.append("missing solved comparison")
        if comparison.get("energy_closure", {}).get("status") != "computed": errors.append("missing energy closure")
    if errors: raise SystemExit("; ".join(errors))


if __name__ == "__main__":
    main()

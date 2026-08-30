"""Reject malformed evidence from the bounded V2 bridging tracer."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    errors = []
    if payload.get("case_id") != "edge-cracked-plate-bridged-v2":
        errors.append("wrong case")
    if payload.get("status") not in {"accepted", "indeterminate"}:
        errors.append("invalid status")
    if "analytical_authority" in payload:
        errors.append("bridged tracer must not claim an analytical authority")
    if "not a path-independent material toughness" not in payload.get("claim_boundary", ""):
        errors.append("missing bridging claim boundary")
    levels = payload.get("levels", [])
    if [level.get("name") for level in levels] != ["coarse", "medium", "fine"]:
        errors.append("wrong mesh levels")
    for level in levels:
        if len(level.get("contours", [])) != 2:
            errors.append(f"wrong contour count for {level.get('name', 'unknown')}")
    if "fine_medium_change_percent" not in payload.get("comparison", {}):
        errors.append("missing convergence comparison")
    if errors:
        raise SystemExit("; ".join(errors))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run every declared V1 mesh level and write its bounded convergence evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def percent_change(left: float, right: float) -> float:
    return abs(left - right) / abs(right) * 100.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-card", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--solver", type=Path, required=True)
    parser.add_argument("--mesh-audit", type=Path, required=True)
    parser.add_argument("--visualizer", type=Path, required=True)
    args = parser.parse_args()

    card = json.loads(args.case_card.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    level_names = ("coarse", "medium", "fine")
    levels = []
    for name, level in zip(level_names, card["mesh_levels"], strict=True):
        directory = args.output / "levels" / name
        directory.mkdir(parents=True, exist_ok=True)
        mesh = directory / "edge-cracked-plate-v1.msh"
        audit = directory / "mesh-audit.json"
        subprocess.run(["python3", str(args.generator), "--case", str(args.case), "--output", str(mesh),
                        "--near-size", str(level["near_tip_mm"]), "--far-size", str(level["far_field_mm"])], check=True)
        subprocess.run([str(args.mesh_audit), str(mesh), str(audit)], check=True)
        subprocess.run(["python3", str(args.solver), "--mesh", str(mesh), "--output", str(directory),
                        "--case-card", str(args.case_card)], check=True)
        summary = json.loads((directory / "solution-summary.json").read_text(encoding="utf-8"))
        contours = summary["fracture_quantity"]["contours"]
        values = [entry["j_mpa_mm"] for entry in contours]
        mean_j = sum(values) / len(values)
        levels.append({"name": name, "near_tip_mm": level["near_tip_mm"], "far_field_mm": level["far_field_mm"],
                       "mesh": json.loads(audit.read_text(encoding="utf-8"))["mesh"], "contours": contours,
                       "mean_j_mpa_mm": mean_j, "contour_spread_percent": percent_change(max(values), min(values))})

    subprocess.run(["python3", str(args.visualizer), "--mesh", str(args.output / "levels" / "medium" / "edge-cracked-plate-v1.msh"),
                    "--output", str(args.output / "case-visual.svg")], check=True)
    target = card["analytical_authority"]["plane_strain_j_mpa_mm"]
    gates = card["fracture_quantity"]["gates"]
    fine, medium = levels[2], levels[1]
    analytical_error = percent_change(fine["mean_j_mpa_mm"], target)
    fine_medium_change = percent_change(fine["mean_j_mpa_mm"], medium["mean_j_mpa_mm"])
    runtime_seconds = time.monotonic() - started
    accepted = (analytical_error <= gates["analytical_error_percent_max"] and
                fine_medium_change <= gates["fine_medium_change_percent_max"] and
                all(level["contour_spread_percent"] <= gates["contour_spread_percent_max"] for level in levels) and
                runtime_seconds <= gates["runtime_seconds_max"])
    write_json(args.output / "provenance-convergence.json", {
        "case_id": card["case_id"], "status": "accepted" if accepted else "indeterminate",
        "runtime": {"seconds_excluding_image_build": runtime_seconds, "limit_seconds": gates["runtime_seconds_max"]},
        "analytical_authority": card["analytical_authority"], "levels": levels,
        "comparison": {"fine_analytical_error_percent": analytical_error,
                       "fine_medium_change_percent": fine_medium_change},
        "gates": gates,
        "adjudication": "accepted numerical reference evidence" if accepted else "indeterminate numerical reference evidence",
        "claim_boundary": "Numerical reference evidence for the declared isotropic plane-strain benchmark only; not CMC calibration, physical validation, qualification, or design authority."
    })


if __name__ == "__main__":
    main()

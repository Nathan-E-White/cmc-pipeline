#!/usr/bin/env python3
"""Orchestrate declared reversible-cohesive mesh levels without owning loading.

The program runner is the sole adapter across the load-program seam.  This
module only creates validated per-level inputs and summarizes its public
artifacts, retaining each program's complete attempt history verbatim.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def percent_change(left: float, right: float) -> float:
    return abs(left - right) / max(abs(right), 1e-30) * 100.0


def final_increment(program: dict) -> dict | None:
    increments = program.get("accepted_increments", [])
    # The final bisection point can be below an earlier accepted overshoot.
    # Program order, rather than maximum displacement, identifies the event.
    return increments[-1] if increments else None


def solved_metrics(program: dict) -> dict | None:
    final = final_increment(program)
    if program.get("status") != "solved" or final is None:
        return None
    reaction = final.get("reaction", {})
    external = final.get("external_work", {})
    bulk = final.get("bulk_strain_energy", {})
    j = final.get("j_diagnostic", {})
    required = (reaction, external, bulk)
    if any(item.get("status") != "computed" for item in required):
        return None
    if j.get("status") != "diagnostic-only":
        return None
    return {
        "reaction_mpa_mm": reaction["value_mpa_mm"],
        "reversible_interface_potential_mpa_mm2": final["reversible_interface_potential_mpa_mm2"],
        "mouth_opening_mm": final["mouth_opening_mm"],
        "external_work_mpa_mm2": external["value_mpa_mm2"],
        "bulk_strain_energy_mpa_mm2": bulk["value_mpa_mm2"],
        "energy_closure": final.get("energy_closure", {"status": "unavailable"}),
        "j_diagnostic": j,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-card", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--generator", type=Path, required=True)
    parser.add_argument("--mesh-audit", type=Path, required=True)
    parser.add_argument("--artifact-validator", type=Path, required=True)
    parser.add_argument("--program-runner", type=Path, required=True)
    parser.add_argument("--single-step-solver", type=Path, required=True)
    parser.add_argument("--visualizer", type=Path, required=True)
    args = parser.parse_args()

    card = json.loads(args.case_card.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    levels = []
    for name, level in zip(("coarse", "medium", "fine"), card["mesh_levels"], strict=True):
        directory = args.output / "levels" / name
        directory.mkdir(parents=True, exist_ok=True)
        mesh = directory / f"{card['case_id']}.msh"
        pairs = directory / "crack-face-pairs.json"
        audit = directory / "mesh-audit.json"
        subprocess.run(["python3", str(args.generator), "--case", str(args.case), "--output", str(mesh),
                        "--near-size", str(level["near_tip_mm"]), "--far-size", str(level["far_field_mm"]),
                        "--crack-face-pairs-output", str(pairs)], check=True)
        subprocess.run([str(args.mesh_audit), str(mesh), str(audit)], check=True)
        subprocess.run(["python3", str(args.artifact_validator), "--mesh", str(mesh), "--pairs", str(pairs)], check=True)
        completed = subprocess.run(["python3", str(args.program_runner), "--mesh", str(mesh),
                                    "--crack-face-pairs", str(pairs), "--case-card", str(args.case_card),
                                    "--solver", str(args.single_step_solver), "--output", str(directory)],
                                   text=True, capture_output=True, check=False)
        program_path = directory / "reversible-cohesive-program.json"
        if program_path.is_file():
            program = json.loads(program_path.read_text(encoding="utf-8"))
        else:
            program = {"status": "failed", "failure": completed.stderr.strip() or completed.stdout.strip() or "program runner did not write an artifact",
                       "attempts": [], "accepted_increments": []}
        metrics = solved_metrics(program)
        level_status = program["status"] if program["status"] != "solved" or metrics is not None else "indeterminate"
        levels.append({"name": name, "near_tip_mm": level["near_tip_mm"], "far_field_mm": level["far_field_mm"],
                       "status": level_status, "program_status": program["status"],
                       "mesh": json.loads(audit.read_text(encoding="utf-8"))["mesh"], "program": program,
                       "metrics": metrics})

    solved = [level for level in levels if level["status"] == "solved" and level["metrics"] is not None]
    failed = [level for level in levels if level["status"] == "failed"]
    status = "failed" if failed else ("solved" if len(solved) == len(levels) else "indeterminate")
    comparison = {"status": "unavailable"}
    if len(solved) == len(levels):
        fine, medium = levels[2]["metrics"], levels[1]["metrics"]
        comparison = {
            "status": "computed", "fine_medium_change_percent": {
                "reaction": percent_change(fine["reaction_mpa_mm"], medium["reaction_mpa_mm"]),
                "reversible_interface_potential": percent_change(fine["reversible_interface_potential_mpa_mm2"], medium["reversible_interface_potential_mpa_mm2"]),
                "mouth_opening_event": percent_change(fine["mouth_opening_mm"], medium["mouth_opening_mm"]),
                "j_diagnostic_by_radius": [
                    {"radius_mm": fine_item["radius_mm"], "change_percent": percent_change(fine_item["j_mpa_mm"], medium_item["j_mpa_mm"])}
                    for fine_item, medium_item in zip(fine["j_diagnostic"]["contours"], medium["j_diagnostic"]["contours"], strict=True)
                ],
            },
            "energy_closure": fine["energy_closure"],
        }
    subprocess.run(["python3", str(args.visualizer), "--mesh", str(args.output / "levels" / "medium" / f"{card['case_id']}.msh"),
                    "--output", str(args.output / "case-visual.svg"), "--case-card", str(args.case_card)], check=True)
    payload = {
        "case_id": card["case_id"], "status": status,
        "runtime": {"seconds_excluding_image_build": time.monotonic() - started},
        "levels": levels, "comparison": comparison,
        "adjudication": "synthetic reversible-cohesive numerical tracer; J is diagnostic only and no toughness or fracture-energy authority is asserted.",
        "claim_boundary": card["claim_boundary"],
    }
    write_json(args.output / "reversible-cohesive-convergence.json", payload)


if __name__ == "__main__":
    main()

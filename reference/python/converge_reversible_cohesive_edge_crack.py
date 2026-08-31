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
from dataclasses import dataclass
from pathlib import Path


def write_json(path: Path, payload: dict) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def tool_failure(completed: subprocess.CompletedProcess[str], tool: str) -> str | None:
    if completed.returncode == 0:
        return None
    detail = completed.stderr.strip() or completed.stdout.strip()
    return detail or f"{tool} exited with status {completed.returncode}"


def percent_change(left: float, right: float) -> float:
    return abs(left - right) / max(abs(right), 1e-30) * 100.0


def final_increment(program: dict) -> dict | None:
    increments = program.get("accepted_increments", [])
    # The final bisection point can be below an earlier accepted overshoot.
    # Program order, rather than maximum displacement, identifies the event.
    return increments[-1] if increments else None


def solved_metrics(program: dict) -> dict | None:
    final = final_increment(program)
    if program.get("status") != "solved" or not isinstance(final, dict):
        return None
    reaction = final.get("reaction", {})
    external = final.get("external_work", {})
    bulk = final.get("bulk_strain_energy", {})
    j = final.get("j_diagnostic", {})
    required = (reaction, external, bulk)
    if any(
        not isinstance(item, dict) or item.get("status") != "computed"
        for item in required
    ):
        return None
    values = (
        reaction.get("value_mpa_mm"),
        final.get("reversible_interface_potential_mpa_mm2"),
        final.get("mouth_opening_mm"),
        external.get("value_mpa_mm2"),
        bulk.get("value_mpa_mm2"),
    )
    if (
        any(
            isinstance(value, bool) or not isinstance(value, (int, float))
            for value in values
        )
        or not isinstance(j, dict)
        or j.get("status") != "diagnostic-only"
        or not isinstance(j.get("contours"), list)
    ):
        return None
    return {
        "reaction_mpa_mm": reaction["value_mpa_mm"],
        "reversible_interface_potential_mpa_mm2": final[
            "reversible_interface_potential_mpa_mm2"
        ],
        "mouth_opening_mm": final["mouth_opening_mm"],
        "external_work_mpa_mm2": external["value_mpa_mm2"],
        "bulk_strain_energy_mpa_mm2": bulk["value_mpa_mm2"],
        "energy_closure": final.get("energy_closure", {"status": "unavailable"}),
        "j_diagnostic": j,
    }


def acceptance_summary(card: dict, status: str, comparison: dict) -> dict:
    """Adjudicate the declared numerical gates without changing level status."""
    gates = card["acceptance"]
    summary = {
        "status": "unavailable",
        "gates": {
            "fine_medium_change_percent_max": gates["fine_medium_change_percent_max"],
            "fine_energy_closure_percent_max": gates["fine_energy_closure_percent_max"],
        },
    }
    if status != "solved" or comparison.get("status") != "computed":
        return summary
    changes = comparison["fine_medium_change_percent"]
    observed = {
        "reaction": changes["reaction"],
        "reversible_interface_potential": changes["reversible_interface_potential"],
        "mouth_opening_event": changes["mouth_opening_event"],
        **{
            f"j_diagnostic_radius_{item['radius_mm']}_mm": item["change_percent"]
            for item in changes["j_diagnostic_by_radius"]
        },
    }
    energy = comparison["energy_closure"]
    if energy.get("status") != "computed":
        return summary
    summary["observed"] = {
        "fine_medium_change_percent": observed,
        "fine_energy_closure_percent": energy["mismatch_percent"],
    }
    refinement_passed = all(
        value <= gates["fine_medium_change_percent_max"] for value in observed.values()
    )
    energy_passed = (
        energy["mismatch_percent"] < gates["fine_energy_closure_percent_max"]
    )
    summary["status"] = (
        "accepted" if refinement_passed and energy_passed else "rejected"
    )
    summary["failed_gates"] = [
        *([] if refinement_passed else ["fine-medium-refinement"]),
        *([] if energy_passed else ["fine-energy-closure"]),
    ]
    return summary


@dataclass(frozen=True)
class ReversibleCohesiveToolchain:
    """Concrete tool adapters kept behind the convergence execution module."""

    artifact_validator: Path
    case: Path
    case_card: Path
    generator: Path
    mesh_audit: Path
    program_runner: Path
    single_step_solver: Path
    visualizer: Path


class ReversibleCohesiveConvergence:
    """Own the declared per-level lifecycle and final numerical artifact."""

    def __init__(self, toolchain: ReversibleCohesiveToolchain) -> None:
        self._tools = toolchain

    def _program(self, directory: Path, mesh: Path, pairs: Path) -> dict:
        completed = subprocess.run(
            [
                "python3",
                str(self._tools.program_runner),
                "--mesh",
                str(mesh),
                "--crack-face-pairs",
                str(pairs),
                "--case-card",
                str(self._tools.case_card),
                "--solver",
                str(self._tools.single_step_solver),
                "--output",
                str(directory),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        program_path = directory / "reversible-cohesive-program.json"
        if completed.returncode != 0 or not program_path.is_file():
            return {
                "status": "failed",
                "failure": "program runner did not write an artifact"
                + (
                    f": {detail}"
                    if (detail := tool_failure(completed, "program runner"))
                    else ""
                ),
                "attempts": [],
                "accepted_increments": [],
            }
        try:
            return json.loads(program_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "status": "indeterminate",
                "failure": "program runner wrote malformed JSON evidence",
                "attempts": [],
                "accepted_increments": [],
            }

    def _run_tool(self, command: list[str], tool: str) -> str | None:
        try:
            completed = subprocess.run(command, text=True, capture_output=True, check=False)
        except OSError as error:
            return f"{tool} could not start: {error}"
        return tool_failure(completed, tool)

    @staticmethod
    def _failed_level(
        name: str, level: dict, failure: str, *, mesh: dict | None = None
    ) -> dict:
        return {
            "name": name,
            "near_tip_mm": level["near_tip_mm"],
            "far_field_mm": level["far_field_mm"],
            "status": "failed",
            "program_status": "unavailable",
            "mesh": mesh,
            "program": {
                "status": "unavailable",
                "failure": failure,
                "attempts": [],
                "accepted_increments": [],
            },
            "metrics": None,
        }

    def _level(self, card: dict, name: str, level: dict, directory: Path) -> dict:
        directory.mkdir(parents=True, exist_ok=True)
        mesh = directory / f"{card['case_id']}.msh"
        pairs = directory / "crack-face-pairs.json"
        audit = directory / "mesh-audit.json"
        failure = self._run_tool(
            [
                "python3",
                str(self._tools.generator),
                "--case",
                str(self._tools.case),
                "--output",
                str(mesh),
                "--near-size",
                str(level["near_tip_mm"]),
                "--far-size",
                str(level["far_field_mm"]),
                "--crack-face-pairs-output",
                str(pairs),
            ],
            "mesh generator",
        )
        if failure is not None:
            return self._failed_level(name, level, failure)
        failure = self._run_tool(
            [str(self._tools.mesh_audit), str(mesh), str(audit)], "mesh audit"
        )
        if failure is not None:
            return self._failed_level(name, level, failure)
        try:
            mesh_record = json.loads(audit.read_text(encoding="utf-8"))["mesh"]
        except (FileNotFoundError, json.JSONDecodeError, KeyError, TypeError):
            return self._failed_level(
                name, level, "mesh audit did not write a usable mesh record"
            )
        failure = self._run_tool(
            [
                "python3",
                str(self._tools.artifact_validator),
                "--mesh",
                str(mesh),
                "--pairs",
                str(pairs),
            ],
            "opened-crack artifact validator",
        )
        if failure is not None:
            return self._failed_level(name, level, failure, mesh=mesh_record)
        program = self._program(directory, mesh, pairs)
        metrics = solved_metrics(program)
        level_status = (
            program["status"]
            if program["status"] != "solved" or metrics is not None
            else "indeterminate"
        )
        return {
            "name": name,
            "near_tip_mm": level["near_tip_mm"],
            "far_field_mm": level["far_field_mm"],
            "status": level_status,
            "program_status": program["status"],
            "mesh": mesh_record,
            "program": program,
            "metrics": metrics,
        }

    def run(self, output: Path) -> dict:
        card = json.loads(self._tools.case_card.read_text(encoding="utf-8"))
        output.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        levels = [
            self._level(card, name, level, output / "levels" / name)
            for name, level in zip(
                ("coarse", "medium", "fine"), card["mesh_levels"], strict=True
            )
        ]
        solved = [
            level
            for level in levels
            if level["status"] == "solved" and level["metrics"] is not None
        ]
        failed = [level for level in levels if level["status"] == "failed"]
        status = (
            "failed"
            if failed
            else ("solved" if len(solved) == len(levels) else "indeterminate")
        )
        comparison = {"status": "unavailable"}
        if len(solved) == len(levels):
            fine, medium = levels[2]["metrics"], levels[1]["metrics"]
            comparison = {
                "status": "computed",
                "fine_medium_change_percent": {
                    "reaction": percent_change(
                        fine["reaction_mpa_mm"], medium["reaction_mpa_mm"]
                    ),
                    "reversible_interface_potential": percent_change(
                        fine["reversible_interface_potential_mpa_mm2"],
                        medium["reversible_interface_potential_mpa_mm2"],
                    ),
                    "mouth_opening_event": percent_change(
                        fine["mouth_opening_mm"], medium["mouth_opening_mm"]
                    ),
                    "j_diagnostic_by_radius": [
                        {
                            "radius_mm": fine_item["radius_mm"],
                            "change_percent": percent_change(
                                fine_item["j_mpa_mm"], medium_item["j_mpa_mm"]
                            ),
                        }
                        for fine_item, medium_item in zip(
                            fine["j_diagnostic"]["contours"],
                            medium["j_diagnostic"]["contours"],
                            strict=True,
                        )
                    ],
                },
                "energy_closure": fine["energy_closure"],
            }
        visual_failure = self._run_tool(
            [
                "python3",
                str(self._tools.visualizer),
                "--mesh",
                str(output / "levels" / "medium" / f"{card['case_id']}.msh"),
                "--output",
                str(output / "case-visual.svg"),
                "--case-card",
                str(self._tools.case_card),
            ],
            "case visualizer",
        )
        return {
            "case_id": card["case_id"],
            "status": status,
            "runtime": {"seconds_excluding_image_build": time.monotonic() - started},
            "levels": levels,
            "comparison": comparison,
            "acceptance": acceptance_summary(card, status, comparison),
            "artifacts": {
                "case_visual": (
                    {"status": "available", "path": "case-visual.svg"}
                    if visual_failure is None
                    else {
                        "status": "failed",
                        "path": "case-visual.svg",
                        "failure": visual_failure,
                    }
                )
            },
            "adjudication": "synthetic reversible-cohesive numerical tracer; J is diagnostic only and no toughness or fracture-energy authority is asserted.",
            "claim_boundary": card["claim_boundary"],
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

    toolchain = ReversibleCohesiveToolchain(
        artifact_validator=args.artifact_validator,
        case=args.case,
        case_card=args.case_card,
        generator=args.generator,
        mesh_audit=args.mesh_audit,
        program_runner=args.program_runner,
        single_step_solver=args.single_step_solver,
        visualizer=args.visualizer,
    )
    payload = ReversibleCohesiveConvergence(toolchain).run(args.output)
    write_json(args.output / "reversible-cohesive-convergence.json", payload)


if __name__ == "__main__":
    main()

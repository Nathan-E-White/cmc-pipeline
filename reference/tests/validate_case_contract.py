#!/usr/bin/env python3
"""Fast contract checks for files consumed by the reference-solver image."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "reference/cases/edge-cracked-plate-v1.geo"
DOCKERFILE = ROOT / "containers/solver.Dockerfile"


def test_geo_declares_fixed_benchmark_envelope() -> None:
    source = GEO.read_text(encoding="utf-8")
    for declaration in (
        "width_mm = 100;",
        "height_mm = 200;",
        "crack_length_mm = 30;",
        'Physical Surface("plate", 1)',
        'Physical Curve("loaded", 2)',
        'Physical Curve("support_y", 3)',
        'Physical Curve("crack_trace", 4)',
        'Physical Curve("crack_faces", 7)',
        'Physical Point("x_anchor", 5)',
    ):
        assert declaration in source


def test_solver_image_is_immutable_and_smoke_tests_its_contents() -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    assert "dolfinx/dolfinx:stable@sha256:" in source
    assert "ctest --test-dir /opt/cmc/build --output-on-failure" in source
    assert "reference-solver verify-case --output /tmp/reference-smoke" in source
    assert "reference-solver solve-case --output /tmp/reference-solve-smoke" in source
    assert "reference-solver converge-bridged-case" in source


def test_case_card_is_explicit_about_the_current_boundary() -> None:
    source = (ROOT / "reference/cases/edge-cracked-plate-v1.json").read_text(encoding="utf-8")
    assert '"status": "plane-strain-solve-with-j"' in source
    assert "reports a numerical domain-integral fracture quantity" in source


def test_case_card_declares_independent_j_contours_and_fixed_gates() -> None:
    source = (ROOT / "reference/cases/edge-cracked-plate-v1.json").read_text(encoding="utf-8")
    assert '"method": "domain-integral"' in source
    assert '"contour_radii_mm": [8, 12]' in source
    assert '"analytical_error_percent_max": 5.0' in source
    assert '"fine_medium_change_percent_max": 2.5' in source
    assert '"contour_spread_percent_max": 2.5' in source


def test_public_runner_declares_the_convergence_artifacts() -> None:
    source = (ROOT / "reference/scripts/reference-solver").read_text(encoding="utf-8")
    assert "converge-case" in source
    assert "converge_edge_crack.py" in source
    assert "render_edge_crack_visual.py" in source


def test_v2_bridged_case_declares_a_fixed_closure_traction_tracer() -> None:
    source = (ROOT / "reference/cases/edge-cracked-plate-bridged-v2.json").read_text(
        encoding="utf-8"
    )
    assert '"case_id": "edge-cracked-plate-bridged-v2"' in source
    assert '"kind": "prescribed-crack-face-closure-traction"' in source
    assert '"crack_growth": "fixed"' in source
    assert "not a traction-separation law" in source


def test_public_runner_declares_the_bridged_tracer_command() -> None:
    source = (ROOT / "reference/scripts/reference-solver").read_text(encoding="utf-8")
    assert "converge-bridged-case" in source
    assert "edge-cracked-plate-bridged-v2.json" in source


def test_container_contract_exercises_the_bridged_artifact_validator() -> None:
    source = (ROOT / "reference/tests/reference_container_test.sh").read_text(encoding="utf-8")
    assert "converge-bridged-case --output /artifacts" in source
    assert "validate_bridged_convergence_artifact.py" in source


def test_solver_image_validates_the_reversible_case_card_before_any_solve() -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    assert "validate_reversible_case.py --case-card /opt/cmc/cases/edge-cracked-plate-reversible-v2.json" in source


def test_solver_image_generates_and_validates_opened_crack_pair_artifacts_at_every_level() -> None:
    source = DOCKERFILE.read_text(encoding="utf-8")
    assert "--crack-face-pairs-output" in source
    assert "validate_opened_crack_mesh_artifacts.py" in source
    for level in ("coarse 2 10", "medium 1 5", "fine 0.5 2.5"):
        assert level in source


def test_public_runner_and_container_validate_the_reversible_cohesive_convergence_artifact() -> None:
    runner = (ROOT / "reference/scripts/reference-solver").read_text(encoding="utf-8")
    container_test = (ROOT / "reference/tests/reference_container_test.sh").read_text(encoding="utf-8")
    assert "converge-reversible-cohesive-case" in runner
    assert "converge_reversible_cohesive_edge_crack.py" in runner
    assert "validate_reversible_cohesive_convergence_artifact.py" in container_test


def _validate_reversible_case(card: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        case_card = Path(directory) / "case.json"
        case_card.write_text(json.dumps(card), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(ROOT / "reference/python/validate_reversible_case.py"),
                "--case-card",
                str(case_card),
            ],
            text=True,
            capture_output=True,
            check=False,
        )


def test_reversible_case_card_declares_the_synthetic_reversible_tracer() -> None:
    case_card = json.loads(
        (ROOT / "reference/cases/edge-cracked-plate-reversible-v2.json").read_text(
            encoding="utf-8"
        )
    )
    result = _validate_reversible_case(case_card)
    assert result.returncode == 0, result.stderr
    assert case_card["mesh_levels"] == [
        {"near_tip_mm": 2, "far_field_mm": 10},
        {"near_tip_mm": 1, "far_field_mm": 5},
        {"near_tip_mm": 0.5, "far_field_mm": 2.5},
    ]


def test_reversible_case_card_rejects_invalid_law_provenance_loading_and_scope() -> None:
    case_card = json.loads(
        (ROOT / "reference/cases/edge-cracked-plate-reversible-v2.json").read_text(
            encoding="utf-8"
        )
    )
    mutations = (
        ("model", "cohesive_interface", "law", "peak_opening_mm"),
        ("model", "cohesive_interface", "provenance", "authority"),
        ("loading", "program", "initial_increment_mm"),
        ("loading", "program", "endpoint", "mouth_opening_mm"),
        ("declared_exclusions",),
    )
    invalid_values = (0.1, "measured", 0.002, 0.09, ["contact"])
    for path, value in zip(mutations, invalid_values, strict=True):
        candidate = json.loads(json.dumps(case_card))
        target = candidate
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        result = _validate_reversible_case(candidate)
        assert result.returncode != 0


if __name__ == "__main__":
    test_geo_declares_fixed_benchmark_envelope()
    test_solver_image_is_immutable_and_smoke_tests_its_contents()
    test_case_card_is_explicit_about_the_current_boundary()
    test_case_card_declares_independent_j_contours_and_fixed_gates()
    test_public_runner_declares_the_convergence_artifacts()
    test_v2_bridged_case_declares_a_fixed_closure_traction_tracer()
    test_public_runner_declares_the_bridged_tracer_command()
    test_container_contract_exercises_the_bridged_artifact_validator()
    test_solver_image_validates_the_reversible_case_card_before_any_solve()
    test_solver_image_generates_and_validates_opened_crack_pair_artifacts_at_every_level()
    test_reversible_case_card_declares_the_synthetic_reversible_tracer()
    test_reversible_case_card_rejects_invalid_law_provenance_loading_and_scope()

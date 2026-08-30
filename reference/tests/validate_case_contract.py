#!/usr/bin/env python3
"""Fast contract checks for files consumed by the reference-solver image."""

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


if __name__ == "__main__":
    test_geo_declares_fixed_benchmark_envelope()
    test_solver_image_is_immutable_and_smoke_tests_its_contents()
    test_case_card_is_explicit_about_the_current_boundary()
    test_case_card_declares_independent_j_contours_and_fixed_gates()
    test_public_runner_declares_the_convergence_artifacts()

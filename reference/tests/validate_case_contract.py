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
    assert '"status": "plane-strain-solve-no-j"' in source
    assert "executes one linear-elastic plane-strain reference solve; it does not yet report J" in source


if __name__ == "__main__":
    test_geo_declares_fixed_benchmark_envelope()
    test_solver_image_is_immutable_and_smoke_tests_its_contents()
    test_case_card_is_explicit_about_the_current_boundary()

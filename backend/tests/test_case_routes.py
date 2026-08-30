from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_lists_representative_fixture_cases() -> None:
    response = client.get("/api/v1/cases")

    assert response.status_code == 200
    payload = response.json()
    assert payload["api_version"] == "v1"
    assert payload["fixture"]["corpus_id"] == "v1-demo-2026-08"
    assert payload["provenance"]["source_kind"] == "fixture"
    assert payload["cases"][0]["case_id"] == "sic-sic-panel-042"


def test_returns_declared_fixture_case_metadata() -> None:
    response = client.get("/api/v1/cases/sic-sic-panel-042")

    assert response.status_code == 200
    assert response.json()["case"] == {
        "label": "SiC/SiC panel 042",
        "architecture": "sic_sic",
        "inputs": {
            "coating_shear_limit_mpa": 60.0,
            "mechanical_load_kn": 45.0,
            "thermal_gradient_c_per_mm": 120.0,
        },
    }


def test_returns_compact_visualisation_mesh() -> None:
    response = client.get("/api/v1/cases/sic-sic-panel-042/mesh")

    assert response.status_code == 200
    assert response.json()["mesh"] == {
        "coordinate_system": "case_local_cartesian_mm",
        "node_count": 640000,
        "vertex_positions_mm": [-1.5, 0.0, 0.0, -1.45, 0.1, -0.02],
        "fiber_indices": [[0, 1, 2]],
    }
    assert response.json()["provenance"]["claim_boundary"] == (
        "Rendering fixture only; not a solver-grade mesh."
    )


def test_returns_recorded_fixture_adjudication() -> None:
    response = client.get("/api/v1/cases/sic-sic-panel-042/adjudication")

    assert response.status_code == 200
    assert response.json()["adjudication"]["status"] == "accepted"
    assert response.json()["adjudication"]["relative_error"] == 0.0242
    assert response.json()["provenance"]["claim_boundary"] == (
        "Fixture adjudication only; not independent physical validation or qualification."
    )


def test_rejects_unknown_case_id_with_declared_error() -> None:
    response = client.get("/api/v1/cases/unknown-case")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "case_not_found"


def test_rejects_malformed_case_id_with_declared_error() -> None:
    response = client.get("/api/v1/cases/not%20a%20slug")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_case_id"


def test_distinguishes_unavailable_mesh_from_unknown_case() -> None:
    response = client.get("/api/v1/cases/c-sic-panel-017/mesh")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "artifact_not_available"


def test_case_collection_rejects_unsupported_methods() -> None:
    response = client.post("/api/v1/cases")

    assert response.status_code == 405
    assert response.headers["allow"] == "GET, HEAD"
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_allows_head_requests_for_fixture_resources() -> None:
    response = client.head("/api/v1/cases")

    assert response.status_code == 200
    assert response.content == b""

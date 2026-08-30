from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def submit_reference_run() -> str:
    response = client.post(
        "/api/v1/reference-runs",
        json={
            "case_id": "sic-sic-panel-042",
            "inputs": {
                "coating_shear_limit_mpa": 60.0,
                "mechanical_load_kn": 45.0,
                "thermal_gradient_c_per_mm": 120.0,
            },
        },
    )
    assert response.status_code == 202
    return response.json()["run"]["run_id"]


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


def test_rejects_a_client_that_does_not_accept_json() -> None:
    response = client.get("/api/v1/cases", headers={"Accept": "text/html"})

    assert response.status_code == 406
    assert response.json()["error"]["code"] == "not_acceptable"


def test_allows_head_requests_for_fixture_resources() -> None:
    response = client.head("/api/v1/cases")

    assert response.status_code == 200
    assert response.content == b""


def test_submits_a_known_fixture_reference_run() -> None:
    response = client.post(
        "/api/v1/reference-runs",
        json={
            "case_id": "sic-sic-panel-042",
            "inputs": {
                "coating_shear_limit_mpa": 60.0,
                "mechanical_load_kn": 45.0,
                "thermal_gradient_c_per_mm": 120.0,
            },
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["run"]["status"] == "queued"
    assert payload["run"]["case_id"] == "sic-sic-panel-042"
    assert payload["fixture"]["corpus_id"] == "v1-demo-2026-08"


def test_observing_a_queued_run_advances_to_its_fixture_terminal_state() -> None:
    run_id = submit_reference_run()

    response = client.get(f"/api/v1/reference-runs/{run_id}")

    assert response.status_code == 200
    assert response.json()["run"] == {
        "run_id": run_id,
        "case_id": "sic-sic-panel-042",
        "status": "complete",
    }


def test_completed_run_exposes_a_versioned_reference_result() -> None:
    run_id = submit_reference_run()
    client.get(f"/api/v1/reference-runs/{run_id}")

    response = client.get(f"/api/v1/reference-runs/{run_id}/results")

    assert response.status_code == 200
    assert response.json()["result"] == {
        "quantity": "j_integral_proxy",
        "value": 12.4,
        "units": "J/m²",
    }
    assert response.json()["fixture"]["revision"] == "1"


def test_verifies_a_matching_surrogate_observation_against_a_reference_run() -> None:
    run_id = submit_reference_run()
    client.get(f"/api/v1/reference-runs/{run_id}")

    response = client.post(
        "/api/v1/simulation/verify",
        json={
            "reference_run_id": run_id,
            "inputs": {
                "coating_shear_limit_mpa": 60.0,
                "mechanical_load_kn": 45.0,
                "thermal_gradient_c_per_mm": 120.0,
            },
            "observation": {
                "quantity": "j_integral_proxy",
                "value": 12.1,
                "units": "J/m²",
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["verification"]["status"] == "accepted"
    assert response.json()["verification"]["relative_error"] == 0.0242


def test_retrieves_a_verification_record_during_the_server_lifetime() -> None:
    run_id = submit_reference_run()
    client.get(f"/api/v1/reference-runs/{run_id}")
    created = client.post(
        "/api/v1/simulation/verify",
        json={
            "reference_run_id": run_id,
            "inputs": {
                "coating_shear_limit_mpa": 60.0,
                "mechanical_load_kn": 45.0,
                "thermal_gradient_c_per_mm": 120.0,
            },
            "observation": {
                "quantity": "j_integral_proxy",
                "value": 12.1,
                "units": "J/m²",
            },
        },
    )

    verification_id = created.json()["verification"]["verification_id"]
    response = client.get(f"/api/v1/simulation/verifications/{verification_id}")

    assert response.status_code == 200
    assert response.json()["verification"]["verification_id"] == verification_id
    assert response.json()["verification"]["status"] == "accepted"


def test_rejects_an_observation_outside_the_fixture_criterion() -> None:
    run_id = submit_reference_run()
    client.get(f"/api/v1/reference-runs/{run_id}")

    response = client.post(
        "/api/v1/simulation/verify",
        json={
            "reference_run_id": run_id,
            "inputs": {
                "coating_shear_limit_mpa": 60.0,
                "mechanical_load_kn": 45.0,
                "thermal_gradient_c_per_mm": 120.0,
            },
            "observation": {
                "quantity": "j_integral_proxy",
                "value": 10.0,
                "units": "J/m²",
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["verification"]["status"] == "rejected"


def test_marks_out_of_domain_observation_indeterminate() -> None:
    run_id = submit_reference_run()
    client.get(f"/api/v1/reference-runs/{run_id}")

    response = client.post(
        "/api/v1/simulation/verify",
        json={
            "reference_run_id": run_id,
            "inputs": {
                "coating_shear_limit_mpa": 60.0,
                "mechanical_load_kn": 45.0,
                "thermal_gradient_c_per_mm": 120.0,
            },
            "observation": {
                "quantity": "j_integral_proxy",
                "value": 12.1,
                "units": "J/m²",
                "domain_status": "outside_declared_domain",
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["verification"]["status"] == "indeterminate"
    assert response.json()["verification"]["relative_error"] is None


def test_rejects_boolean_observation_values() -> None:
    run_id = submit_reference_run()
    client.get(f"/api/v1/reference-runs/{run_id}")

    response = client.post(
        "/api/v1/simulation/verify",
        json={
            "reference_run_id": run_id,
            "inputs": {
                "coating_shear_limit_mpa": 60.0,
                "mechanical_load_kn": 45.0,
                "thermal_gradient_c_per_mm": 120.0,
            },
            "observation": {"quantity": "j_integral_proxy", "value": True, "units": "J/m²"},
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_observation"


def test_rejects_unknown_or_mismatched_reference_run_submissions() -> None:
    unknown_case = client.post(
        "/api/v1/reference-runs",
        json={"case_id": "unknown-case", "inputs": {}},
    )
    mismatched_inputs = client.post(
        "/api/v1/reference-runs",
        json={"case_id": "sic-sic-panel-042", "inputs": {}},
    )

    assert unknown_case.status_code == 404
    assert unknown_case.json()["error"]["code"] == "case_not_found"
    assert mismatched_inputs.status_code == 422
    assert mismatched_inputs.json()["error"]["code"] == "input_mismatch"


def test_does_not_expose_a_result_before_a_reference_run_is_complete() -> None:
    run_id = submit_reference_run()

    response = client.get(f"/api/v1/reference-runs/{run_id}/results")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "reference_run_not_complete"


def test_rejects_verification_when_declared_inputs_do_not_match_the_run() -> None:
    run_id = submit_reference_run()
    client.get(f"/api/v1/reference-runs/{run_id}")

    response = client.post(
        "/api/v1/simulation/verify",
        json={
            "reference_run_id": run_id,
            "inputs": {},
            "observation": {
                "quantity": "j_integral_proxy",
                "value": 12.1,
                "units": "J/m²",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "input_mismatch"

"""Versioned representative data exposed by the V1 fixture API."""

CORPUS_ID = "v1-demo-2026-08"
CLAIM_BOUNDARY = (
    "Comparison evidence within the declared numerical model; not experimental truth "
    "or a qualified structural prediction."
)

CASES = {
    "sic-sic-panel-042": {
        "label": "SiC/SiC panel 042",
        "architecture": "sic_sic",
        "revision": "1",
        "inputs": {
            "coating_shear_limit_mpa": 60.0,
            "mechanical_load_kn": 45.0,
            "thermal_gradient_c_per_mm": 120.0,
        },
        "mesh": {
            "coordinate_system": "case_local_cartesian_mm",
            "node_count": 640000,
            "vertex_positions_mm": [-1.5, 0.0, 0.0, -1.45, 0.1, -0.02],
            "fiber_indices": [[0, 1, 2]],
        },
        "adjudication": {
            "status": "accepted",
            "quantity": "j_integral_proxy",
            "reference_value": 12.4,
            "surrogate_value": 12.1,
            "relative_error": 0.0242,
            "acceptance_criterion": {"maximum_relative_error": 0.05},
            "units": "J/m²",
        },
    },
    "c-sic-panel-017": {
        "label": "C/SiC panel 017",
        "architecture": "c_sic",
        "revision": "1",
        "inputs": {
            "coating_shear_limit_mpa": 48.0,
            "mechanical_load_kn": 38.0,
            "thermal_gradient_c_per_mm": 95.0,
        },
    },
}


def fixture_descriptor(case_id: str | None = None) -> dict[str, str]:
    fixture = {"corpus_id": CORPUS_ID, "kind": "representative"}
    if case_id is not None:
        fixture.update({"case_id": case_id, "revision": CASES[case_id]["revision"]})
    return fixture


def provenance(case_id: str | None = None, *, mesh: bool = False, adjudication: bool = False) -> dict:
    if case_id is None:
        return {
            "source_kind": "fixture",
            "claim_boundary": "Representative fixture metadata only.",
        }

    value = {
        "source_kind": "fixture",
        "reference_solution": {
            "model_id": "demo-cmc-fracture-model",
            "solver_configuration_id": "demo-config-r1",
            "discretization_id": "demo-mesh-r1",
        },
        "claim_boundary": CLAIM_BOUNDARY,
    }
    if mesh:
        value["claim_boundary"] = "Rendering fixture only; not a solver-grade mesh."
    if adjudication:
        value["surrogate"] = {"model_id": "demo-fno-r1", "domain_id": "demo-domain-r1"}
        value["claim_boundary"] = (
            "Fixture adjudication only; not independent physical validation or qualification."
        )
    return value

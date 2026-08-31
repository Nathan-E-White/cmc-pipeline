"""Versioned representative data exposed by the V1 fixture API."""

CORPUS_ID = "v1-demo-2026-08"
CLAIM_BOUNDARY = (
    "Comparison evidence within the declared numerical model; not experimental truth "
    "or a qualified structural prediction."
)

_CASES = {
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
    "layered-tufroc-panel-009": {
        "label": "Layered fibrous insulation panel 009",
        "architecture": "layered_tufroc",
        "revision": "1",
        "inputs": {
            "coating_shear_limit_mpa": 35.0,
            "mechanical_load_kn": 52.0,
            "thermal_gradient_c_per_mm": 175.0,
        },
        "mesh": {
            "coordinate_system": "case_local_cartesian_mm",
            "node_count": 310000,
            "vertex_positions_mm": [-1.0, 0.0, 0.0, -0.96, 0.08, -0.03],
            "fiber_indices": [[0, 1, 2]],
        },
        "adjudication": {
            "status": "accepted",
            "quantity": "j_integral_proxy",
            "reference_value": 9.8,
            "surrogate_value": 10.0,
            "relative_error": 0.0204,
            "acceptance_criterion": {"maximum_relative_error": 0.05},
            "units": "J/m²",
        },
    },
}


class FixtureCorpus:
    """Own versioned V1 fixture facts, availability, and provenance."""

    def find(self, case_id: str) -> dict | None:
        return _CASES.get(case_id)

    def inputs(self, case_id: str) -> dict:
        return self.require(case_id)["inputs"]

    def require(self, case_id: str) -> dict:
        case = self.find(case_id)
        if case is None:
            raise KeyError(case_id)
        return case

    def descriptor(self, case_id: str | None = None) -> dict[str, str]:
        fixture = {"corpus_id": CORPUS_ID, "kind": "representative"}
        if case_id is not None:
            fixture.update({"case_id": case_id, "revision": self.require(case_id)["revision"]})
        return fixture

    def provenance(
        self, case_id: str | None = None, *, mesh: bool = False, adjudication: bool = False
    ) -> dict:
        if case_id is None:
            return {"source_kind": "fixture", "claim_boundary": "Representative fixture metadata only."}
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
            value["claim_boundary"] = "Fixture adjudication only; not independent physical validation or qualification."
        return value

    def list_cases(self) -> list[dict]:
        return [
            {
                "case_id": case_id,
                "label": case["label"],
                "architecture": case["architecture"],
                "availability": {
                    "adjudication": "available" if "adjudication" in case else "unavailable",
                    "mesh": "available" if "mesh" in case else "unavailable",
                },
            }
            for case_id, case in _CASES.items()
        ]

    def case_metadata(self, case_id: str) -> dict:
        case = self.require(case_id)
        return {key: case[key] for key in ("label", "architecture", "inputs")}

    def mesh(self, case_id: str) -> dict | None:
        return self.require(case_id).get("mesh")

    def adjudication(self, case_id: str) -> dict | None:
        return self.require(case_id).get("adjudication")

    def result(self, case_id: str) -> dict | None:
        adjudication = self.adjudication(case_id)
        if adjudication is None:
            return None
        return {
            "quantity": adjudication["quantity"],
            "value": adjudication["reference_value"],
            "units": adjudication["units"],
        }


fixture_corpus = FixtureCorpus()

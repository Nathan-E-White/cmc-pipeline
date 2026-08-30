"""In-memory fixture workflow records for the V1 HTTP boundary."""

from itertools import count

from app.fixture_corpus import CASES


class FixtureWorkflowError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


class ReferenceRunService:
    def __init__(self) -> None:
        self._run_ids = count(1)
        self._runs: dict[str, dict] = {}

    def submit(self, case_id: object, inputs: object) -> dict:
        if not isinstance(case_id, str):
            raise FixtureWorkflowError(422, "invalid_reference_run", "A case_id is required.")
        case = CASES.get(case_id)
        if case is None:
            raise FixtureWorkflowError(
                404, "case_not_found", "No fixture case exists for the supplied identifier."
            )
        if inputs != case["inputs"]:
            raise FixtureWorkflowError(
                422,
                "input_mismatch",
                "Reference-run inputs must match the declared fixture case inputs.",
            )

        run_id = f"run-{next(self._run_ids):04d}"
        run = {"run_id": run_id, "case_id": case_id, "status": "queued"}
        self._runs[run_id] = run
        return run

    def observe(self, run_id: str) -> dict:
        run = self._runs.get(run_id)
        if run is None:
            raise FixtureWorkflowError(
                404, "reference_run_not_found", "No reference run exists for the supplied identifier."
            )
        if run["status"] == "queued":
            run["status"] = "complete"
        return run

    def result(self, run_id: str) -> tuple[dict, dict]:
        run = self._runs.get(run_id)
        if run is None:
            raise FixtureWorkflowError(
                404, "reference_run_not_found", "No reference run exists for the supplied identifier."
            )
        if run["status"] != "complete":
            raise FixtureWorkflowError(
                409, "reference_run_not_complete", "The reference run has not reached a terminal state."
            )
        adjudication = CASES[run["case_id"]].get("adjudication")
        if adjudication is None:
            raise FixtureWorkflowError(
                404, "artifact_not_available", "No result fixture is available for this reference run."
            )
        return run, {
            "quantity": adjudication["quantity"],
            "value": adjudication["reference_value"],
            "units": adjudication["units"],
        }


class VerificationService:
    def __init__(self, reference_runs: ReferenceRunService) -> None:
        self._reference_runs = reference_runs
        self._verification_ids = count(1)
        self._verifications: dict[str, dict] = {}

    def verify(self, reference_run_id: object, inputs: object, observation: object) -> tuple[dict, dict]:
        if not isinstance(reference_run_id, str):
            raise FixtureWorkflowError(
                422, "invalid_verification", "A reference_run_id is required."
            )
        run, result = self._reference_runs.result(reference_run_id)
        if inputs != CASES[run["case_id"]]["inputs"]:
            raise FixtureWorkflowError(
                422,
                "input_mismatch",
                "Verification inputs must match the declared reference-run inputs.",
            )
        if not isinstance(observation, dict):
            raise FixtureWorkflowError(422, "invalid_observation", "An observation object is required.")
        if (
            observation.get("quantity") != result["quantity"]
            or observation.get("units") != result["units"]
            or isinstance(observation.get("value"), bool)
            or not isinstance(observation.get("value"), (int, float))
        ):
            raise FixtureWorkflowError(
                422,
                "invalid_observation",
                "Observation quantity, units, and numeric value must match the fixture result.",
            )

        criterion = CASES[run["case_id"]]["adjudication"]["acceptance_criterion"]
        if observation.get("domain_status") == "outside_declared_domain":
            status = "indeterminate"
            relative_error = None
            comparison_note = "Observation is outside the declared fixture surrogate domain."
        else:
            relative_error = round(abs(observation["value"] - result["value"]) / abs(result["value"]), 4)
            status = "accepted" if relative_error <= criterion["maximum_relative_error"] else "rejected"
            comparison_note = None
        verification_id = f"verification-{next(self._verification_ids):04d}"
        verification = {
            "verification_id": verification_id,
            "reference_run_id": reference_run_id,
            "status": status,
            "quantity": result["quantity"],
            "reference_value": result["value"],
            "surrogate_value": observation["value"],
            "relative_error": relative_error,
            "acceptance_criterion": criterion,
            "units": result["units"],
        }
        if comparison_note is not None:
            verification["comparison_note"] = comparison_note
        self._verifications[verification_id] = verification
        return run, verification

    def get(self, verification_id: str) -> dict:
        verification = self._verifications.get(verification_id)
        if verification is None:
            raise FixtureWorkflowError(
                404,
                "verification_not_found",
                "No verification record exists for the supplied identifier.",
            )
        return verification

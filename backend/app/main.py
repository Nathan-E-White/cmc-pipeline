"""HTTP boundary for the fixture-backed V1 API."""

import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.fixture_corpus import CASES, fixture_descriptor, provenance
from app.fixture_workflow import FixtureWorkflowError, ReferenceRunService, VerificationService

app = FastAPI(title="CMC Pipeline Fixture API", version="v1")
_CASE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
reference_runs = ReferenceRunService()
verifications = VerificationService(reference_runs)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"api_version": "v1", "error": {"code": code, "message": message}},
    )


@app.middleware("http")
async def normalise_method_not_allowed(request: Request, call_next):
    response = await call_next(request)
    if response.status_code != 405:
        return response
    headers = {}
    if allow := response.headers.get("allow"):
        if allow == "GET":
            allow = "GET, HEAD"
        headers["Allow"] = allow
    return JSONResponse(
        status_code=405,
        content={
            "api_version": "v1",
            "error": {
                "code": "method_not_allowed",
                "message": "This resource does not allow the requested method.",
            },
        },
        headers=headers,
    )


def require_case(case_id: str):
    if not _CASE_ID.fullmatch(case_id):
        return None, error_response(400, "invalid_case_id", "The supplied identifier is not a valid slug.")
    case = CASES.get(case_id)
    if case is None:
        return None, error_response(404, "case_not_found", "No fixture case exists for the supplied identifier.")
    return case, None


@app.post("/api/v1/reference-runs", status_code=202)
def submit_reference_run(request: dict):
    try:
        run = reference_runs.submit(request.get("case_id"), request.get("inputs"))
    except FixtureWorkflowError as error:
        return error_response(error.status_code, error.code, error.message)
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(run["case_id"]),
        "provenance": provenance(run["case_id"]),
        "run": run,
    }


@app.get("/api/v1/reference-runs/{run_id}")
def get_reference_run(run_id: str):
    try:
        run = reference_runs.observe(run_id)
    except FixtureWorkflowError as error:
        return error_response(error.status_code, error.code, error.message)
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(run["case_id"]),
        "provenance": provenance(run["case_id"]),
        "run": run,
    }


@app.get("/api/v1/reference-runs/{run_id}/results")
def get_reference_run_result(run_id: str):
    try:
        run, result = reference_runs.result(run_id)
    except FixtureWorkflowError as error:
        return error_response(error.status_code, error.code, error.message)
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(run["case_id"]),
        "provenance": provenance(run["case_id"]),
        "result": result,
    }


@app.post("/api/v1/simulation/verify", status_code=201)
def verify_simulation(request: dict):
    try:
        run, verification = verifications.verify(
            request.get("reference_run_id"), request.get("inputs"), request.get("observation")
        )
    except FixtureWorkflowError as error:
        return error_response(error.status_code, error.code, error.message)
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(run["case_id"]),
        "provenance": provenance(run["case_id"], adjudication=True),
        "verification": verification,
    }


@app.get("/api/v1/simulation/verifications/{verification_id}")
def get_verification(verification_id: str):
    try:
        verification = verifications.get(verification_id)
        run = reference_runs.observe(verification["reference_run_id"])
    except FixtureWorkflowError as error:
        return error_response(error.status_code, error.code, error.message)
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(run["case_id"]),
        "provenance": provenance(run["case_id"], adjudication=True),
        "verification": verification,
    }


@app.head("/api/v1/cases")
@app.get("/api/v1/cases")
def list_cases() -> dict:
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(),
        "provenance": provenance(),
        "cases": [
            {
                "case_id": case_id,
                "label": case["label"],
                "architecture": case["architecture"],
                "availability": {
                    "adjudication": "available" if "adjudication" in case else "unavailable",
                    "mesh": "available" if "mesh" in case else "unavailable",
                },
            }
            for case_id, case in CASES.items()
        ],
    }


@app.head("/api/v1/cases/{case_id}")
@app.get("/api/v1/cases/{case_id}")
def get_case(case_id: str):
    case, error = require_case(case_id)
    if error:
        return error
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(case_id),
        "provenance": provenance(case_id),
        "case": {key: case[key] for key in ("label", "architecture", "inputs")},
    }


@app.head("/api/v1/cases/{case_id}/mesh")
@app.get("/api/v1/cases/{case_id}/mesh")
def get_mesh(case_id: str):
    case, error = require_case(case_id)
    if error:
        return error
    if "mesh" not in case:
        return error_response(404, "artifact_not_available", "No mesh fixture is available for this case.")
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(case_id),
        "provenance": provenance(case_id, mesh=True),
        "mesh": case["mesh"],
    }


@app.head("/api/v1/cases/{case_id}/adjudication")
@app.get("/api/v1/cases/{case_id}/adjudication")
def get_adjudication(case_id: str):
    case, error = require_case(case_id)
    if error:
        return error
    if "adjudication" not in case:
        return error_response(
            404, "artifact_not_available", "No adjudication fixture is available for this case."
        )
    return {
        "api_version": "v1",
        "fixture": fixture_descriptor(case_id),
        "provenance": provenance(case_id, adjudication=True),
        "adjudication": case["adjudication"],
    }

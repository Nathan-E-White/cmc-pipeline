"""HTTP boundary for the read-only V1 fixture corpus."""

import re

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.fixture_corpus import CASES, fixture_descriptor, provenance

app = FastAPI(title="CMC Pipeline Fixture API", version="v1")
_CASE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"api_version": "v1", "error": {"code": code, "message": message}},
    )


@app.middleware("http")
async def enforce_read_only_contract(request: Request, call_next):
    response = await call_next(request)
    if response.status_code != 405:
        return response
    return JSONResponse(
        status_code=405,
        content={
            "api_version": "v1",
            "error": {"code": "method_not_allowed", "message": "V1 is read-only."},
        },
        headers={"Allow": "GET, HEAD"},
    )


def require_case(case_id: str):
    if not _CASE_ID.fullmatch(case_id):
        return None, error_response(400, "invalid_case_id", "The supplied identifier is not a valid slug.")
    case = CASES.get(case_id)
    if case is None:
        return None, error_response(404, "case_not_found", "No fixture case exists for the supplied identifier.")
    return case, None


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

"""Read-side V3 run-register API; V1 fixture routes remain deliberately separate."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.run_mirror import PostgresRunMirror, RunMirrorError

router = APIRouter(prefix="/api/v3", tags=["v3-run-register"])


class SubmitRun(BaseModel):
    case_card: dict


def mirror() -> PostgresRunMirror:
    dsn = os.environ.get("CMC_RUN_MIRROR_DSN")
    if not dsn:
        raise HTTPException(503, "V3 Run Mirror is not configured.")
    return PostgresRunMirror(dsn)


@router.get("/runs")
def list_runs(after_revision: int = 0) -> dict:
    if after_revision:
        return {"api_version": "v3", "runs": mirror().summaries(after_revision)}
    runs, register_sequence = mirror().register_snapshot()
    return {
        "api_version": "v3",
        "runs": runs,
        "register_sequence": register_sequence,
    }


@router.post("/runs", status_code=202)
def submit_run(request: SubmitRun, idempotency_key: str = Header(alias="Idempotency-Key")) -> dict:
    try:
        snapshot = mirror().submit(request.case_card, idempotency_key)
    except RunMirrorError as error:
        raise HTTPException(422, str(error)) from error
    return {"api_version": "v3", "run": snapshot.__dict__}


@router.post("/runs/{run_id}/cancel")
def cancel_run(run_id: str) -> dict:
    try:
        snapshot = mirror().request_cancel(run_id)
    except (RunMirrorError, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    return {"api_version": "v3", "run": snapshot.__dict__}


@router.get("/runs/{run_id}/details")
def detail_page(
    run_id: str, phase: str, before_sequence: int | None = None, limit: int = 5
) -> dict:
    try:
        details, next_before = mirror().detail_page(run_id, phase, before_sequence, limit)
    except (RunMirrorError, ValueError) as error:
        raise HTTPException(422, str(error)) from error
    return {"api_version": "v3", "details": details, "next_before_sequence": next_before}


async def event_stream(run_id: str, after_sequence: int) -> AsyncIterator[str]:
    """Resume by sequence.  SSE exposes compact update notices, never raw payloads."""
    sequence = after_sequence
    while True:
        try:
            events = mirror().stream(run_id, sequence)
        except RunMirrorError, ValueError:
            yield 'event: error\ndata: {"code":"run_not_found"}\n\n'
            return
        for event in events:
            sequence = event.run_sequence
            yield f"id: {sequence}\nevent: revision\ndata: {json.dumps({'revision': sequence})}\n\n"
        yield ": keepalive\n\n"
        await asyncio.sleep(1)


async def register_stream(after_sequence: int) -> AsyncIterator[str]:
    """Publish compact projection revisions for every register row after a snapshot."""
    sequence = after_sequence
    while True:
        for event in mirror().register_events(sequence):
            sequence = int(event["register_sequence"])
            yield f"id: {sequence}\nevent: revision\ndata: {json.dumps({'register_sequence': sequence})}\n\n"
        yield ": keepalive\n\n"
        await asyncio.sleep(1)


@router.get("/events")
def register_events(after_sequence: int = 0) -> StreamingResponse:
    return StreamingResponse(
        register_stream(after_sequence),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/runs/{run_id}/events")
def run_events(run_id: str, after_sequence: int = 0) -> StreamingResponse:
    return StreamingResponse(
        event_stream(run_id, after_sequence),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )

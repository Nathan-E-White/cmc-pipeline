"""Declared local runners and their outcome contracts."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.field_set import DeclaredFieldSet


@dataclass(frozen=True)
class RunnerDefinition:
    service: str
    command: tuple[str, ...]
    success_outcome: str
    evidence_disposition: str
    phase_key: str
    event_type: str
    success_warning: str
    failure_warning: str
    requires_artifact_manifest: bool = False
    artifact_validator: Callable[[dict[str, tuple[str, str]]], None] | None = None
    terminal_phase_key: str = "publish"
    terminal_success_event_type: str = "attempt-finished"
    terminal_failure_event_type: str = "attempt-failed"
    terminal_success_warning: str = (
        "Declared verification completed; it does not establish a solved physical case."
    )
    terminal_failure_warning: str = "Runner exited nonzero; artifacts remain available for review."


RUNNERS = {
    "reference-solver": RunnerDefinition(
        "reference-solver",
        ("verify-case", "--output", "/artifacts"),
        "indeterminate",
        "indeterminate",
        "verify",
        "verification-observed",
        "Verification completed; no numerical solution outcome is asserted.",
        "Runner exited nonzero; inspect published artifacts.",
    ),
    "r0-field-export": RunnerDefinition(
        "reference-solver",
        ("export-r0-field-case", "--output", "/artifacts"),
        "solved",
        "accepted",
        "publish",
        "field-export-observed",
        "Accepted local reference field export; not physical validation.",
        "Field export runner exited nonzero; inspect published artifacts.",
        True,
        DeclaredFieldSet.validate_declared_files,
        "publish",
        "field-export-finished",
        "field-export-failed",
        "Accepted local reference field export completed; not physical validation.",
        "Field export failed; published artifacts remain available for review.",
    ),
}


def runner_definition(runner_key: str) -> RunnerDefinition:
    try:
        return RUNNERS[runner_key]
    except KeyError as error:
        raise ValueError(f"Runner {runner_key!r} is not declared.") from error

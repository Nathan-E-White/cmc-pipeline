"""Declared local runners and their outcome contracts."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunnerDefinition:
    service: str
    command: tuple[str, ...]
    success_outcome: str
    evidence_disposition: str


RUNNERS = {
    "reference-solver": RunnerDefinition(
        "reference-solver",
        ("verify-case", "--output", "/artifacts"),
        "indeterminate",
        "indeterminate",
    ),
    "r0-field-export": RunnerDefinition(
        "reference-solver",
        ("export-r0-field-case", "--output", "/artifacts"),
        "solved",
        "accepted",
    ),
}


def runner_definition(runner_key: str) -> RunnerDefinition:
    try:
        return RUNNERS[runner_key]
    except KeyError as error:
        raise ValueError(f"Runner {runner_key!r} is not declared.") from error

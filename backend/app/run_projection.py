"""Bounded, human-facing projections of normalized run evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PhaseEvidence:
    phase_key: str
    state: str
    headline: dict[str, Any]
    residual: float | None
    container_observed_at: str | None
    solver_evidence_at: str | None


@dataclass(frozen=True)
class EvidenceSummary:
    phase_key: str
    state: str
    headline: dict[str, Any]
    trend: dict[str, Any]
    last_container_observed_at: str | None
    last_solver_evidence_at: str | None


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    revision: int
    phase: EvidenceSummary


class RunRegisterProjection:
    """Hide trend decimation and factual summary construction behind one seam."""

    def __init__(self, maximum_trend_samples: int = 32) -> None:
        self._maximum_trend_samples = maximum_trend_samples
        self._summaries: dict[str, RunSummary] = {}

    def apply(self, run_id: str, revision: int, evidence: PhaseEvidence) -> RunSummary:
        existing = self._summaries.get(run_id)
        samples: list[float] = []
        if existing and existing.phase.phase_key == evidence.phase_key:
            samples = list(existing.phase.trend.get("samples", []))
        if evidence.residual is not None and evidence.residual > 0:
            samples.append(evidence.residual)
        samples = samples[-self._maximum_trend_samples :]
        trend = {"kind": "log-residual", "samples": samples} if samples else {}
        summary = RunSummary(
            run_id,
            revision,
            EvidenceSummary(evidence.phase_key, evidence.state, evidence.headline, trend,
                            evidence.container_observed_at, evidence.solver_evidence_at),
        )
        self._summaries[run_id] = summary
        return summary

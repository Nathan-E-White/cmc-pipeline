from app.run_projection import PhaseEvidence, RunRegisterProjection


def test_projection_keeps_a_bounded_log_residual_trend_and_factual_timestamps() -> None:
    projection = RunRegisterProjection(maximum_trend_samples=3)
    phase = PhaseEvidence(
        phase_key="solve",
        state="running",
        headline={"iteration": 4, "limit": 25, "residual": 1.0e-4},
        residual=1.0e-4,
        container_observed_at="2026-09-01T12:00:00Z",
        solver_evidence_at="2026-09-01T11:59:58Z",
    )
    for residual in (1.0, 0.1, 0.01, 0.001):
        phase = PhaseEvidence(
            phase_key="solve", state="running", headline={"residual": residual}, residual=residual,
            container_observed_at="2026-09-01T12:00:00Z", solver_evidence_at="2026-09-01T11:59:58Z",
        )
        summary = projection.apply("run-1", 1, phase)

    assert summary.revision == 1
    assert summary.phase.trend == {"kind": "log-residual", "samples": [0.1, 0.01, 0.001]}
    assert summary.phase.last_container_observed_at == "2026-09-01T12:00:00Z"
    assert summary.phase.last_solver_evidence_at == "2026-09-01T11:59:58Z"


def test_projection_does_not_infer_a_stalled_state_from_elapsed_time() -> None:
    summary = RunRegisterProjection().apply(
        "run-1", 7,
        PhaseEvidence(phase_key="solve", state="running", headline={}, residual=None,
                      container_observed_at="old", solver_evidence_at="older"),
    )
    assert summary.phase.state == "running"

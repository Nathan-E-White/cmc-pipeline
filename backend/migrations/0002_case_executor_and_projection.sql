ALTER TABLE runs ADD COLUMN evidence_disposition TEXT
    CHECK (evidence_disposition IN ('accepted', 'rejected', 'indeterminate', 'unavailable'));

ALTER TABLE run_events ADD COLUMN phase_key TEXT;

CREATE TABLE run_attempts (
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    runner_key TEXT NOT NULL,
    container_name TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL CHECK (state IN ('queued', 'running', 'terminal')),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    last_container_observed_at TIMESTAMPTZ,
    exit_code INTEGER,
    PRIMARY KEY (run_id, attempt_number)
);

CREATE TABLE run_summary_projections (
    run_id UUID PRIMARY KEY REFERENCES runs(run_id) ON DELETE CASCADE,
    revision INTEGER NOT NULL CHECK (revision > 0),
    lifecycle TEXT NOT NULL,
    outcome TEXT,
    evidence_disposition TEXT,
    current_phase_key TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE run_phase_summary_projections (
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    phase_key TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision > 0),
    state TEXT NOT NULL CHECK (state IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    headline JSONB NOT NULL DEFAULT '{}'::jsonb,
    trend JSONB NOT NULL DEFAULT '{}'::jsonb,
    warnings JSONB NOT NULL DEFAULT '[]'::jsonb,
    last_container_observed_at TIMESTAMPTZ,
    last_solver_evidence_at TIMESTAMPTZ,
    PRIMARY KEY (run_id, phase_key)
);

CREATE INDEX run_events_by_phase ON run_events (run_id, phase_key, run_sequence);

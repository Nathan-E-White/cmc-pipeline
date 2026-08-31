CREATE TABLE case_cards (
    case_digest CHAR(64) PRIMARY KEY,
    card JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE runs (
    run_id UUID PRIMARY KEY,
    case_digest CHAR(64) NOT NULL REFERENCES case_cards(case_digest),
    idempotency_key TEXT NOT NULL UNIQUE,
    lifecycle TEXT NOT NULL CHECK (lifecycle IN ('submitted', 'admitted', 'running', 'cancel-requested', 'terminal')),
    outcome TEXT CHECK (outcome IN ('solved', 'failed', 'cancelled', 'indeterminate')),
    current_attempt INTEGER NOT NULL DEFAULT 1 CHECK (current_attempt > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((lifecycle = 'terminal') = (outcome IS NOT NULL))
);

CREATE TABLE run_events (
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    attempt_number INTEGER NOT NULL CHECK (attempt_number > 0),
    run_sequence INTEGER NOT NULL CHECK (run_sequence > 0),
    sequence INTEGER NOT NULL CHECK (sequence > 0),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, attempt_number, sequence),
    UNIQUE (run_id, run_sequence)
);

CREATE TABLE artifacts (
    sha256 CHAR(64) PRIMARY KEY,
    byte_length BIGINT NOT NULL CHECK (byte_length >= 0),
    media_type TEXT NOT NULL,
    storage_key TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE run_artifacts (
    run_id UUID NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    sha256 CHAR(64) NOT NULL REFERENCES artifacts(sha256),
    PRIMARY KEY (run_id, role)
);

-- A register cursor is global, unlike each run's local evidence sequence.
ALTER TABLE run_events ADD COLUMN register_sequence BIGSERIAL;
CREATE INDEX run_events_by_register_sequence ON run_events (register_sequence);

# V3 Run Mirror contract

## Status and claim boundary

This contract defines the first local-development persistence slice of V3. It records an operational workflow; it does not execute a solver, calibrate a material model, validate a result, or establish a production HPC deployment. V1 fixture routes remain separate and retain their existing semantics.

## Module and interface

The **Run Mirror** is the authoritative local record for a submitted immutable case card, lifecycle decision, attempt-ordered event sequence, and artifact metadata. Its caller-facing interface is deliberately small:

```text
submit(case_card, idempotency_key) -> RunSnapshot
inspect(run_id) -> RunSnapshot
request_cancel(run_id) -> RunSnapshot
stream(run_id, after_sequence) -> ordered RunEvent[]
```

`submit` canonicalises the JSON case card and persists its SHA-256 digest. The same idempotency key returns the original run only when it names the same case digest; a different case is refused. Events have a run-global `run_sequence` for resumable streaming and an `(attempt_number, sequence)` pair for attempt-local ordering; sequence starts at one for every attempt. The initial attempt is one. A restart reconstructs `inspect` and `stream` from Postgres rather than process memory.

Lifecycle is one of `submitted`, `admitted`, `running`, `cancel-requested`, or `terminal`; outcome is independently `solved`, `failed`, `cancelled`, or `indeterminate` only at terminal lifecycle. A cancellation request is a lifecycle fact, not a claim that a container has stopped.

## Artifact identity

MinIO is an immutable content-addressed store. An artifact key is `sha256/<hex digest>` and Postgres records its SHA-256, byte length, media type, and role on a run. Retrieval rechecks the digest; a mismatch is unavailable evidence, not an empty artifact. The browser and future executors consume the metadata record, never an inferred path.

## Ownership and exclusions

Postgres, not Electric or the browser, authorizes lifecycle decisions and owns the ordered event log. Electric is configured only as a read-projection replicator. Numbered migrations in [`../backend/migrations`](../backend/migrations) are the schema authority and are applied once by the local Compose `migrate` module. HTTP/SSE resume notices and container-originated events are implemented local-development delivery items; the Field Artifact module separately converts accepted declared field evidence. Workflow compilation remains later work.

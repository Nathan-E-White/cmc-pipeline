# Research note: honest backend progress reporting for scientific runs

## Scope and current boundary

This is a planning note for a **mirror of backend activity**, not a proposal to
build a new frontend.  Its purpose is to make a long-running scientific job
legible without turning uncertain numerical work into reassuring but invented
percentages or ETAs.

The repository has a useful execution substrate: the local reference container
generates meshes, audits them, runs one or more solves, and writes convergence
and per-program JSON artifacts.  The reversible cohesive path already records
accepted increments, rejected attempts, Newton iteration counts, cutbacks,
failure/indeterminate outcomes, and total runtime.  The present FastAPI
service is explicitly fixture-backed, keeps run state only in memory, and
changes a submitted `queued` run to `complete` when it is observed.  It is
therefore a V1 contract demonstrator, not evidence of a durable job controller
or a live progress source.

The proposal below assumes a future runner can emit structured events at known
boundaries.  It does not assume Argo, a cluster scheduler, a database, or a
browser.  A CLI and an offline artifact reader are first-class consumers.

## What “progress” can honestly mean

For a nonlinear FE calculation, work is not generally a fixed list of equal
units.  Newton convergence, load cutbacks, recovery after a transient
infrastructure fault, adaptive remeshing, and a failed acceptance gate can
all increase or terminate work after it began.  PETSc exposes nonlinear-solver
monitors precisely because residual and iteration state are useful runtime
observations, not because they constitute a completion guarantee. [PETSc SNES
monitoring](https://petsc.org/release/manual/snes/#monitoring-snes-iterations)

Use three different labels and never substitute one for another:

| Label | Honest meaning | Do not imply |
| --- | --- | --- |
| **Lifecycle state** | The durable controller decision: submitted, admitted, running, cancel-requested, terminal. | That the numerical result is valid. |
| **Phase and evidence** | The latest completed or active named unit: `mesh.medium.audit`, `solve.fine.increment`, `convergence.adjudicate`; plus measurable counters and artifacts. | A universal percentage. |
| **Outcome/claim status** | `solved`, `failed`, or `indeterminate`, with the declared gate and artifact. | Experimental validation, qualification, or a material-property claim. |

For this repository, a phase plan can be known before launch: admission;
container/image preparation; for each declared mesh level generate and audit;
run the program; then compare/adjudicate and publish.  A phase percentage is
permissible only when its denominator is declared and stable (for example,
`completed_mesh_levels / 3` after the case card has fixed three levels).  An
accepted load increment is useful as `accepted=7`, `attempted=11`, current
load/displacement and current residual; it is not honestly “70% complete”
unless the remaining program is fixed and no event bracket/cutback can change
it.  Report `progress: unknown` where that proof is absent.

An ETA is optional derived telemetry, not state.  Initially show “not enough
completed comparable work”; later provide a range only from comparable prior
runs (same immutable image/digest, case-card digest, mesh level, execution
class, and resource allocation), its sample count, and the observation time.
Invalidate or mark stale an estimate after a cutback/restart, a material
resource change, or a version/input change.  Never calculate an ETA from a
single Newton residual or from nominal percentage alone.

## Durable state, event history, and telemetry have separate jobs

The canonical run record must be durable and queryable after a worker,
backend, or client restart.  It owns identity, desired action, current
lifecycle state, terminal outcome, latest sequence number, request identity,
input/image/artifact digests, timestamps, and links to immutable artifacts.
An append-only event stream explains *how* it reached that snapshot.  A
materialized “latest status” view can be rebuilt from the event stream and
serves fast polling.

Logs, metrics, and traces are supporting evidence, not the job-state
authority.  Logs retain diagnostic narrative; metrics aggregate rates and
resource behaviour; traces show causal latency across request, controller,
worker, and artifact store.  OpenTelemetry's log model separates source event
time from collection-observation time and includes resource, instrumentation
scope, severity, attributes, and optional trace context—useful fields for an
export adapter, but not a substitute for the run ledger. [OpenTelemetry Logs
Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/)

There is a practical reason not to promote observability to authority: trace
sampling can produce non-recording spans and span limits can discard events or
attributes; OTLP delivery acknowledges only a client/server hop and allows
partial rejection, loss on non-retryable failure, and duplication after an
unacknowledged send.  Those trade-offs make an OTel export an inadmissible sole
record of scientific progress. [OpenTelemetry trace sampling and
limits](https://opentelemetry.io/docs/specs/otel/trace/sdk/#sampling) and
[OTLP reliability](https://opentelemetry.io/docs/specs/otlp/)

At minimum, correlate every record with `run_id`; add `attempt_id`, `worker_id`,
`case_id`, `case_card_digest`, `image_digest`, and an OTel/W3C trace ID where
one exists.  Trace context is for correlation across process boundaries, not
proof that an event was persisted; W3C deliberately defines propagation and
sampling flags rather than a durable delivery protocol. [W3C Trace
Context](https://www.w3.org/TR/trace-context/)

## Event contract and provenance

Make one small versioned, domain-owned envelope.  It may be carried as a
CloudEvent later, but the scientific fields should remain readable without a
telemetry vendor.  CloudEvents supplies interoperable event metadata such as
an identifier, source, type, subject, and time; it does not define the
simulation's state machine. [CloudEvents
specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md)

```json
{
  "schema": "cmc.run-event.v1",
  "event_id": "uuid", "sequence": 41,
  "run_id": "run-…", "attempt_id": "attempt-2",
  "kind": "increment.accepted",
  "occurred_at": "2026-08-31T…Z", "observed_at": "2026-08-31T…Z",
  "phase": {"name": "solve.fine", "state": "running"},
  "measure": {"accepted_increments": 7, "attempts": 11,
              "newton_iterations": 4, "relative_residual": 2e-9},
  "progress": {"value": null, "basis": "unknown"},
  "provenance": {"case_card_digest": "sha256:…", "image_digest": "sha256:…"},
  "artifact": {"uri": "…", "digest": "sha256:…"}
}
```

`sequence` is strictly increasing within a run attempt.  Consumers deduplicate
by `event_id`, reject a conflicting duplicate, detect sequence gaps, and read
the snapshot or replay from the durable event log after a gap.  Keep both
`occurred_at` and `observed_at`; a delayed offline worker upload must not look
as though the calculation happened at upload time.  Version the schema,
enumerate event kinds, and put numerical values with units and declared
meaning in the payload.  Never stream raw solver stdout as the contract.

Suggested initial kinds are `run.submitted`, `run.admitted`, `phase.started`,
`artifact.written`, `increment.attempted`, `increment.rejected`,
`increment.accepted`, `gate.failed`, `cancel.requested`, `checkpoint.written`,
`run.failed`, `run.indeterminate`, and `run.solved`.  Retain enough immutable
provenance to reproduce an interpretation: code/image digest, case card and
mesh digest, solver/library versions, command/argument digest, execution
environment class, parent/retry relationship, and artifact digests.  The
current repository's synthetic/non-calibrated and diagnostic-only boundaries
belong in final result provenance as well as the progress feed.

## Failure, cancellation, retry, and checkpoints

Terminal states must be distinguishable: `solved`, `failed`, `cancelled`, and
`indeterminate`.  `failed` means a defined computation or declared gate
failed; `indeterminate` means the result cannot be responsibly classified
(for example, worker loss after a possible artifact write, a missing required
artifact, or an incomplete convergence set).  A successful process exit is
not itself `solved`; the repository's existing convergence gates illustrate
why numerical adjudication must be explicit.

Cancellation is a state transition, not a signal delivered directly to a
solver process.  Record the request durably, acknowledge it to the requester,
ask the worker to stop at a declared safe point, then write `cancelled` only
after the worker acknowledges stop or the controller has resolved the attempt.
The safe point for the cohesive program is between accepted increments or
after an atomic artifact/checkpoint write—not half-way through overwriting a
result.  If the worker becomes unreachable, retain `cancel-requested` or move
to `indeterminate` according to a stated timeout policy; do not assert a stop
that was not observed.

A retry creates a new `attempt_id`, preserves its parent and original request
identity, and cannot overwrite previous logs, artifacts, or terminal evidence.
Retry only an explicitly classified transient failure; do not retry numerical
nonconvergence or a failed validation gate by default.  A checkpoint must be
atomic, versioned, immutable after publication, bound to case/image/mesh and
solver configuration digests, and validated before resume.  It is acceptable
to begin with *no resumability*: say so and retain restart evidence rather
than emitting the comforting fiction of “resuming.”

## Delivery to a mirror, CLI, and offline users

Start with a snapshot endpoint and event replay:

1. `GET /runs/{id}` returns the durable snapshot, latest sequence, stale
   indicator, terminal/claim status, and artifact links.
2. `GET /runs/{id}/events?after=40` returns an ordered bounded page; the
   client reconnects from the last committed sequence.
3. The CLI can poll these endpoints, or tail a run-local JSONL/event artifact
   while offline.  It prints a one-line phase/counter summary and links exact
   artifact paths; it never requires a browser.
4. Only after polling/replay is useful, add Server-Sent Events (SSE) as a
   one-way convenience stream over the same event sequence.  The HTML standard
   defines automatic EventSource reconnection and an event ID / `Last-Event-ID`
   mechanism, but replay still needs server-side retention and authorization.
   [HTML Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html)

WebSockets are justified only when the mirror truly needs bidirectional live
control beyond ordinary HTTP cancellation.  Do not make a stream socket the
only record of progress, and do not couple a worker's solver loop to client
connection health.  For a future external workflow engine, translate its
status into this contract at one controller boundary; retain the upstream ID
and raw event reference as provenance rather than exposing engine-specific
state as the scientific truth.  A scheduler can honestly report allocation and
execution lifecycle but not solver advancement: Kubernetes Job terminal/retry
state is controller state, while Slurm distinguishes pending, running,
completing, and terminal states. [Kubernetes Job
concept](https://kubernetes.io/docs/concepts/workloads/controllers/job/) and
[Slurm job states](https://slurm.schedmd.com/job_state_codes.html) Label “last
observed scheduler state” and “last confirmed application checkpoint” with
their source and freshness rather than flattening both into a progress bar.

## Security, volume, and retention

Progress can disclose case identifiers, filesystem/object-store paths, host
names, image digests, input geometry, stack traces, and potentially regulated
material data.  Authorize per run/project before both snapshot and stream;
use opaque run IDs; scope cancellation separately from read access; redact
paths/tokens/exception bodies; and audit requests, cancellation, and artifact
downloads.  The stream must not bypass the same authorization applied to the
snapshot.

Treat every event as untrusted at ingress: validate schema, field length,
numeric finiteness, units, event kind, and provenance references.  Bound event
rate and payload size, coalesce high-frequency solver-monitor samples into a
latest value plus a periodic durable sample, and preserve exceptional events
(cutback, gate failure, cancellation) losslessly.  Metrics must avoid
unbounded-cardinality labels such as raw `run_id`; OpenTelemetry cautions that
metrics timeseries are distinguished by name and attributes, so high-cardinality
attributes multiply distinct series. [OpenTelemetry Metrics Data
Model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/)

Set separate retention policies: the compact ledger and required scientific
artifacts survive long enough for reproducibility; verbose solver logs and
dense monitor samples may expire sooner with their loss disclosed.  A mirror
should show `last_observed_at`, source availability, and whether it is reading
live, replayed, fixture, or offline evidence so transport failure cannot look
like an idle healthy calculation.

## Adoption sequence for this repository

1. **Define the contract beside the solver, without transport.**  Add a
   run-event schema, state-transition table, stable IDs/digests, and a
   file-backed JSONL writer.  Instrument only phase boundaries and the
   reversible program's accepted/rejected increment evidence already produced
   in artifacts.  Validate monotonic sequence, terminal immutability, and
   provenance completeness with fixtures.
2. **Make the runner authoritative.**  Have the reference command write a
   durable final snapshot plus append-only events even when it fails.  Map the
   current artifact outcomes faithfully; do not change their numerical
   authority.  Exercise success, cutback exhaustion, cancelled-at-safe-point,
   worker-loss/indeterminate, and duplicate-event recovery.
3. **Expose read-only status.**  Replace neither solver nor artifact contract:
   add snapshot/replay endpoints to a durable backend store and a CLI renderer.
   The existing fixture API can host static contract examples, but must label
   them `fixture` and never simulate live advancement on GET.
4. **Add SSE as a mirror optimization.**  Reuse sequence/replay semantics,
   rate limits, redaction, and authorization.  Verify disconnect, reconnect,
   duplicate, gap, worker restart, and offline catch-up before claiming live
   progress is reliable.
5. **Only then integrate an orchestrator and richer observability.**  Add
   controller adapters, OTel export, traces, dashboards, estimates, and
   checkpoint/resume where measured operating evidence justifies them.

## Limitations and questions to settle before implementation

- Which actual execution boundary owns the run ledger: local container
  wrapper, a future scheduler adapter, or both?  The answer determines
  cancellation authority and durability requirements.
- Are run artifacts local-only, shared-volume, or object-store records?  This
  determines atomic publish, access control, and offline behaviour.
- Which planned phases have fixed denominators for each command?  Do not
  expose a global percentage until each one is written in the case/program
  contract.
- What is the acceptable retained evidence and privacy classification for
  mesh/geometry, input cards, logs, and host metadata?
- Is restart from checkpoint a required capability, or is reliable
  stop-and-restart sufficient for the first scientific workflow?
- What observations are comparable enough to estimate a duration?  Until this
  is answered empirically, the correct ETA is “unknown.”

## Primary sources

- [PETSc SNES manual: monitoring nonlinear solver iterations](https://petsc.org/release/manual/snes/#monitoring-snes-iterations).  First-party solver documentation for iteration/residual monitoring.
- [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/).  Stable first-party specification for event/log timestamps, resources, attributes, severity, and trace correlation.
- [OpenTelemetry Metrics Data Model](https://opentelemetry.io/docs/specs/otel/metrics/data-model/).  First-party specification for metric identity and attributes.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/).  Primary specification for distributed trace-context propagation.
- [OpenTelemetry trace SDK: sampling and span limits](https://opentelemetry.io/docs/specs/otel/trace/sdk/#sampling), and [OTLP reliability](https://opentelemetry.io/docs/specs/otlp/).  First-party specifications for telemetry loss/limits and delivery scope.
- [CloudEvents specification](https://github.com/cloudevents/spec/blob/main/cloudevents/spec.md).  CNCF-owned event metadata specification.
- [WHATWG HTML: Server-Sent Events](https://html.spec.whatwg.org/multipage/server-sent-events.html).  Primary specification for EventSource reconnect and event IDs.
- [Kubernetes Job concept](https://kubernetes.io/docs/concepts/workloads/controllers/job/) and [Slurm job-state codes](https://slurm.schedmd.com/job_state_codes.html).  First-party scheduler lifecycle references.

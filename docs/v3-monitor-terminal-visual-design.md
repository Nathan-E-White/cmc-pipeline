# V3 monitor and terminal visual design

## Decision

The browser monitor and future terminal monitor are two adapters over one
backend **Operational Presentation** module. They show the same durable facts
with different layouts. Neither adapter decides lifecycle, numerical outcome,
or artifact acceptance.

This is design-only. It adds no Argo cluster, terminal program, PINN, solver
progress estimate, or physical-validity claim.

## Existing facts to preserve

- The **Run Mirror** owns lifecycle, outcome, ordered events, attempts, and
  artifact metadata. Electric and SSE are read-side transport only.
- The browser **V3RunRegister** already has compact projections, bounded
  EvidenceSummary detail, and factual container/solver timestamps.
- Hera `rendered` or `validated` will be compiler evidence, not a Kubernetes
  submission or an execution result.
- A future PINN is experimental/report-only. It can be blocked, unavailable,
  incompatible, or out-of-domain without changing the reference result.
- An ONNX inference package is reusable surrogate machinery. Browser-local
  evaluation is allowed only for a backend-admitted declared case and remains
  experimental; it is not a browser-side reference solver.

## Deep module: Operational Presentation

The module owns the translation from durable run, workflow, field, and
surrogate evidence into a bounded human-readable view. Its one public
interface is:

```text
present(run_id, detail_cursor?) -> OperationalView | PresentationUnavailable
```

`detail_cursor` is opaque and requests only an older bounded evidence page.
Injected adapters provide Run Mirror, workflow receipts, Field Artifact, and
PINN observations. The module returns no raw event payload, database row,
container log, MinIO path, or inferred liveness.

```text
OperationalView
  identity: run, attempt, case digest, local-development claim boundary
  reference: lifecycle, current phase, outcome/disposition, factual evidence
  workflow: requested | rendered | validated | submitted | observed | unavailable
  surrogate: not-requested | corpus-blocked | queued | evaluating |
             experimental | out-of-domain | unavailable
  evidence: bounded phase cards, artifact roles/digests, reasons, page cursor
```

The **Depth** is in hiding replay, projection joins, state normalisation, phase
labels, source precedence, evidence paging, and the uncomfortable combinations
of reference/Argo/PINN state. Browser and terminal callers learn one
**Interface** and one vocabulary.

`PresentationUnavailable` is a first-class result with a reason:
`run_not_found`, `projection_unavailable`, `workflow_receipt_unavailable`, or
`surrogate_observation_unavailable`. It is not a blank screen with a spinner.

### Invariants

1. Run Mirror lifecycle/outcome/disposition wins over scheduler status. Argo
   can explain execution; it cannot decide a CMC result.
2. Only the Run Mirror supplies the displayed numerical outcome. A workflow may
   succeed while reference evidence remains `indeterminate`.
3. An accepted reference field comes only from Field Artifact. A PINN field is
   separate and explicitly experimental.
4. `rendered` and `validated` are compiler receipts, never synonyms for
   `submitted`, `running`, or cluster evidence.
5. Timestamps are shown as facts. No adapter infers stale, stuck, progress,
   percentage-complete, or ETA from elapsed time.
6. Browser and terminal receive identical state words, reasons, and digests.

## Browser monitor adapter

The Run Register remains an index. Selecting a run opens a calm **Run Brief**
with a vertical reading order, not three competing status lights:

```text
CMC Pipeline / local-development projection        run 7f3…  attempt 1
Reference evidence                                 solved / accepted
Case 38d… · field artifact available · evidence timestamps recorded

Reference lane
  Admitted — Mesh/Audit — Reference — Adjudicate — Publish
  [the observed phase has its bounded EvidenceSummary card]

Workflow lane
  Hera: rendered and validated locally
  Digest: sha256:…  Cluster submission: not observed.
  [Open declared DAG] [Copy workflow receipt]

Surrogate lane
  PINN: corpus blocked — multi-case accepted R0 corpus required.
  It did not participate in the reference outcome.
```

The reference lane is visually dominant. Workflow and surrogate lanes are
secondary evidence cards. A residual trace appears only when samples exist.
There is no empty chart, radial gauge, synthetic throughput number, green PINN
score, or celebration because a container exited.

When a release has a verified ONNX inference package, the Surrogate Evidence
Summary may state `ONNX available for this declared case` with the package and
parity-receipt digests. Its action is `Evaluate experimental field`, not
`Solve`, `Accept`, or `Replace reference`. A refusal states the exact reason
(for example case incompatibility, OOD envelope, unsupported browser runtime,
or unavailable export). The monitor never treats cached local inference as a
Run Mirror event unless a later server-owned workflow records it.

Normal actions are inspect-only: expand/load older evidence, inspect an
accepted reference field, copy an evidence receipt, and open a rendered
workflow artifact. Cancellation remains distinct: it records a request rather
than declaring that work stopped.

### Separate browser applications and transport roles

The frontend workspace contains two independently runnable/deployable browser
adapters, deliberately not one commingled application:

```text
Monitor application
  Electric Shapes: compact Run Register rows
  global SSE: compact register-revision notice after snapshot
  action: deep-link `physics-result` with run identity

Physics presentation application
  HTTP: selected-run Field Artifact and Operational Presentation reads
  optional run-scoped SSE: compact revision notice only, then refetch the
    normalized selected-run view
  action: render the physics result / permitted experimental inference package
```

The monitor remains the register/index and owns no field renderer.  The physics
presentation application does not subscribe to Electric Shapes or the global
register stream, reconstruct a Run Register, or infer lifecycle/numerical
state.  A run-scoped revision notice is allowed only as cache invalidation for
an already selected run; it carries no raw event payload and is not a second
event interpreter.  The backend's Operational Presentation module must expose
a bounded selected-run read with a monotonic presentation revision so both an
initial HTTP response and a later refetch mean the same thing.

Cross-application navigation carries only an opaque `run_id` (and, if needed
for an explicitly immutable receipt view, a declared digest).  It never passes
Electric offsets, SSE cursors, field arrays, surrogate tensors, credentials, or
claimed status in browser storage/query state.  An unavailable selected run is
rendered from `PresentationUnavailable`, not inferred from a missing monitor
row.

## Terminal monitor adapter

The terminal formats exactly the same `OperationalView`; it does not poll
Docker, Argo, MinIO, or Postgres independently. Its default is a stable,
one-screen brief for logs, SSH, and copy/paste:

```text
$ cmc monitor run 7f3…
CMC PIPELINE / V3 LOCAL-DEVELOPMENT PROJECTION
Run 7f3…  attempt 1  case 38d…
Reference  terminal: solved / accepted
Phase      publish completed | container observed 2026-… | solver evidence 2026-…
Field      available displacement / mm artifact sha256:…

Workflow   Hera rendered + validated locally sha256:…
           cluster submission: not observed
PINN       corpus blocked; declared multi-case accepted R0 corpus required
           reference outcome: unaffected
Evidence   5 newest publish observations; use --older <cursor>
```

The planned terminal **Interface** is deliberately small:

```text
cmc monitor run <run-id> [--older <cursor>] [--format text|json]
cmc monitor watch <run-id>
cmc monitor register
```

Text is normal operational output. JSON is an explicit automation/debugging
choice and serializes the normalized `OperationalView`, not raw events.
`watch` redraws only on a new presentation revision or an explicit connection
change; it prints factual source condition on loss/reconnect and never makes a
countdown, timer-derived alarm, or busy animation.

## State wording

| Lane | State | Display wording | Must not imply |
| --- | --- | --- | --- |
| Reference | `running` | `Reference stage observed running` | percentage or physical correctness |
| Reference | `indeterminate` | `Reference evidence did not establish an outcome` | failure or an accepted field |
| Workflow | `rendered` | `Hera workflow rendered; not submitted` | Kubernetes execution |
| Workflow | `validated` | `Rendered workflow passed declared local validation` | cluster admission or scheduling |
| Workflow | `submitted` | `Submission receipt recorded; scheduler observation pending` | solver start or success |
| Workflow | `observed` | `Scheduler observation recorded: <fact>` | Run Mirror outcome authority |
| PINN | `corpus-blocked` | `No release: accepted multi-case corpus is incomplete` | model training/inference |
| PINN | `experimental` | `PINN screening observation; reference outcome unaffected` | reference replacement/validation |
| PINN | `out-of-domain` | `PINN observation withheld outside declared domain` | reference failure |
| Any | `unavailable` | `Evidence unavailable: <specific reason>` | no work or inferred failure |

These labels are a bounded presentation of facts, not a new lifecycle state
machine. Every lane carries provenance: case digest, workflow digest, or
model/input digests as appropriate.

## Seam placement

```text
Postgres Run Mirror ----\
Workflow receipt adapter --+--> Operational Presentation --> browser monitor
Field Artifact adapter ----/                              \-> terminal monitor
PINN observation adapter -/
```

Electric remains a compact-projection **Adapter** for the monitor register.
Selected run detail comes from Operational Presentation in the physics
application and terminal adapters. A terminal must not duplicate backend SQL or
state interpretation merely because plain text is addictive.

The deletion test is favourable: removing this **Module** forces every monitor
to reconstruct accepted-field, Argo-receipt, missing-surrogate, and factual
liveness rules. It earns its keep.

## Tests at the interface

1. Browser and terminal receive identical `OperationalView` state words,
   digests, and reasons for the same durable records.
2. A `rendered` receipt displays `not submitted`; it cannot look running,
   submitted, or terminal.
3. Argo scheduler success beside a Run Mirror `indeterminate` outcome leaves
   the reference lane indeterminate and states the difference visibly.
4. A PINN `experimental`, `out-of-domain`, or unavailable observation changes
   neither reference outcome nor Field Artifact availability.
5. The field affordance appears only for a Field Artifact `available` response.
6. Detail pages remain bounded and cursor-stable; normal rendering never pulls
   raw unbounded event payloads.
7. An old timestamp remains an old timestamp: no `stalled`, ETA, percentage,
   or freshness alarm appears without an explicit recorded fact.
8. JSON returns normalized presentation; normal terminal output remains concise.
9. An ONNX package is offered only for its declared compatible case and is
   labelled experimental; local inference cannot render as reference acceptance
   or lifecycle progress.
10. The monitor can deep-link a run to the physics application without passing
    client state; the physics application reaches the same bounded selected-run
    view from that `run_id` alone.
11. The physics application contains neither Electric nor global-register SSE
    transport.  If run-scoped invalidation is enabled, it refetches a normalized
    presentation revision and does not parse or persist an event payload.

## Delivery order

1. Define `OperationalView` plus presentation/refusal tests in the backend with
   in-memory adapters; do not alter browser layout first.
2. Add a selected-run presentation route and use it for browser expanded detail.
3. Implement the terminal formatter and snapshot-test screen/paged forms.
4. Add workflow lane receipts after Item 6 render/validation exists.
5. Add the PINN lane only with corpus/release/screen records; until then show
   honest `corpus-blocked`, not an empty model panel.

## Rejected designs

- **Separate browser and terminal business rules:** shallow duplication that
  will disagree about whether Argo or a PINN has authority.
- **A generic log/JSON viewer as normal operation:** a diagnostic escape hatch,
  not a usable operational monitor.
- **An embedded live Argo dashboard:** makes cluster state look authoritative
  and is premature before a real cluster adapter exists.
- **A PINN accuracy dial:** it replaces held-out metrics and provenance with
  dashboard theatre.
- **Time-derived health labels or fake progress:** elapsed time is not a solver
  diagnosis.

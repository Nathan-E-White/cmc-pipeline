# V3 Workflow Compiler and physics-constrained surrogate design

## Status and decision

This is a design for Item 6 and a later, optional surrogate lane. It records
local-development architecture, not a Kubernetes deployment, model
calibration, physical validation, qualification, or design authority.

The existing V3 authority remains unchanged:

- **Run Mirror** owns admission, lifecycle, ordered events, and terminal
  outcome in Postgres.
- **Case Executor** owns one local attempt at a time and publishes declared
  outputs only after validating them.
- **MinIO** stores immutable digest-addressed bytes. Containers do not receive
  its credentials and do not write to it.
- **Field Artifact** is the only browser-facing interpretation of accepted
  XDMF/HDF5 field evidence.

Argo is therefore an execution **adapter**, not a second scheduler of record.
A PINN is a report-only surrogate, not a substitute for the declared reference
solve or its acceptance gates.

## The seams to preserve

```text
case card + attempt
        |
        v
  Run Mirror ----> Case Executor ----> Workflow Execution adapter
     |                    |                    |
     |                    |                    +-- Compose DAG adapter (now)
     |                    |                    +-- Hera/Argo adapter (render only first)
     |                    |
     |                    +--> manifest validation --> MinIO digest store
     v
ordered events and projections

accepted reference artifacts --> Physics-constrained surrogate --> observation
                                                        |
                                                        +--> report-only event/artifacts
```

The compiler must not write lifecycle rows, let Argo mutate Postgres directly,
or give workflow tasks broad storage credentials. The surrogate must not alter
reference acceptance, terminal outcome, or the Field Artifact for the reference
run.

## Deep module: Workflow Compiler

### Interface

The public interface is deliberately one operation:

```text
compile(AttemptPlan) -> CompiledWorkflow | WorkflowRefusal
```

`AttemptPlan` is supplied by the Case Executor after the Run Mirror has
admitted an attempt. It contains only:

- `run_id`, `attempt_number`, and immutable `case_digest`;
- the canonical case card and declared `workflow_key`;
- the declared image digests, command arguments, input artifact receipts, and
  cancellation/retry policy; and
- the selected execution target: `compose-equivalent` or `hera-render`.

`CompiledWorkflow` contains canonical rendered YAML bytes, its SHA-256,
workflow identity, an ordered stage inventory, and a target-neutral execution
plan. It is an artifact candidate, not evidence that a workflow was submitted
to Kubernetes. `WorkflowRefusal` is structured: `unknown_workflow`,
`unresolved_image`, `unsupported_retry_policy`, `invalid_case_card`, or
`invalid_render`.

The compiler internally performs case-card checks, workflow catalog lookup,
topological ordering, image-digest checks, Hera construction/rendering, and
YAML validation. Keeping those details behind one interface gives callers a
stable object to record and test rather than teaching each caller how to build
Argo templates.

### Workflow catalog and adapters

Replace the future use of a free-form Argo YAML file with a small, versioned
**Workflow Catalog** inside the compiler implementation. A catalog entry
declares stage keys, dependencies, runner images by digest, declared commands,
input/output roles, and the only permitted retry/cancel behaviour. The first
entry is `r0-reference-field-export/v1`:

```text
admit -> mesh-audit -> reference-field-export -> adjudicate -> publish
                                                    |
                                                    +-> surrogate-evaluate (optional, report-only)
```

`admit` remains a Run Mirror action, not an Argo task. `publish` is an
executor-owned collector action: it validates the manifest in its scoped
scratch area and publishes the resulting receipts. In a future cluster adapter,
the collector receives narrow credentials; solver tasks receive none.

There are two real adapters at the same seam:

- **ComposeWorkflowExecution** runs the compiler's target-neutral stage plan
  locally, using the existing trusted local Docker arrangement. It is the
  execution proof for Item 6.
- **HeraWorkflowExecution** first renders and validates an Argo `Workflow`
  document from that same plan. It does not submit to a cluster in this item.
  A later adapter may submit and observe it, but it must report observations
  through the Case Executor and Run Mirror rather than connect tasks to the
  database.

The current `Runner.execute(ExecutionRequest)` seam is too small for this:
`ExecutionRequest` does not contain the immutable case card or stage plan. The
successor `AttemptPlan` should be obtained atomically with claiming the
attempt, or fetched by `case_digest` before any execution starts. Do not make
the compiler query Postgres itself; that would turn it into a concealed Run
Mirror implementation.

### Events, cancellation, and artifacts

The execution adapter reports stage observations to the Case Executor, which
uses the Run Mirror to append them. Required stage event types are
`workflow-rendered`, `stage-started`, `stage-finished`, `stage-failed`, and
`workflow-refused`. They include only run/attempt/workflow/stage identity,
image digest, exit state, and declared artifact roles; logs and raw paths stay
in scoped artifacts.

Cancellation remains an idempotent Run Mirror lifecycle fact. The execution
adapter may request cancellation from Compose or Argo, but may not write a
terminal `cancelled` outcome until observation establishes it. Automatic retry
is disallowed in the first catalog because it would change attempt ordering and
evidence meaning. A later retry policy must create a new Run Mirror attempt;
Argo retries inside a hidden task are not an acceptable substitute.

The compiler output itself is published as
`workflow/<workflow-key>/rendered-yaml` with its digest and compilation inputs
recorded. This makes later review possible without pretending that rendered
YAML was executed.

### Tests that cross the interface

1. The same `AttemptPlan` renders byte-for-byte-identical YAML and digest.
2. Unknown workflow keys, mutable image tags, undeclared inputs, cycles, and
   retry policies are refused before an adapter starts work.
3. Hera renders valid YAML with the catalog's declared dependencies, inputs,
   commands, and image digests; no Kubernetes credentials or client are needed.
4. The Compose adapter executes the same stage inventory in dependency order,
   and produces the same declared manifest roles as its compiled plan.
5. A stage failure and a cancellation request preserve ordered Run Mirror
   events and never publish an accepted reference artifact accidentally.
6. The collector rejects path traversal, an undeclared role, and digest
   mismatch. Solver tasks demonstrably cannot publish to MinIO directly.

## Deep module: Physics-constrained surrogate

### Scope of the first problem

The first problem is deliberately R0 only: the declared, fixed-geometry,
two-dimensional plane-strain elastic reference case with its opened paired
crack faces and displacement-controlled loading. It excludes crack advance,
irreversible damage, contact, friction, fibre fragmentation, thermal coupling,
and fatigue. Those are separate R1--R7 case families, not knobs to add to a
first network because neural networks have no natural aversion to scope creep.

The model is a **crack-enriched variational PINN**. The mesh supplies element
quadrature, boundary labels, material regions, and the auditable paired-lip
map; it is not silently flattened into an ordinary FNO grid. The network's
displacement field is enriched so that it can represent the declared opening
across the crack:

\[
u_\theta(x; p) = u_D(x; p) + H_\Gamma(x)a_\theta(x; p)
                   + \sqrt r\,b_\theta(x; p),
\]

where \(u_D\) imposes prescribed displacement data, \(H_\Gamma\) is derived
from the declared crack geometry and paired-lip identity, and the tip term is
an optional declared enrichment. This is not a claim that the network resolves
an arbitrary singular crack field; its applicability is limited to the stated
case card and enrichment policy.

For small-strain plane strain, the internal physics loss is evaluated from
first derivatives at mesh quadrature points:

\[
\epsilon(u)=\tfrac12(\nabla u+\nabla u^T),\quad
\sigma=\mathbb C:\epsilon,\quad
\mathcal L = \lambda_E\left|\Pi_\theta-\Pi_{\rm ext}\right|
 +\lambda_D\mathcal L_D+\lambda_T\mathcal L_T
 +\lambda_R\mathcal L_{\rm reference}.
\]

Here \(\mathcal L_D\) enforces declared Dirichlet conditions,
\(\mathcal L_T\) traction-free crack faces and declared Neumann data, and the
optional reference term compares against accepted training fields only. A
domain-integral calculation of \(J\) is reported using the same declared
contour/domain convention as the reference case; it is not inferred from an
unlabelled loss value.

### Interface

The public module is **PhysicsConstrainedSurrogate**:

```text
release(AcceptedReferenceCorpus, PinnRecipe) -> ModelRelease | ModelRefusal
screen(ModelRelease, DeclaredPinnCase) -> SurrogateObservation | ObservationRefusal
prepare(ModelRelease, DeclaredPinnCase, BrowserRuntimeProfile)
  -> BrowserInferencePackage | InferenceRefusal
```

`release` accepts only a corpus whose members have accepted Field Set evidence,
case-card digest, mesh/pair-map digest, material/kinematic declaration, and
case-level split assignment. It returns a digest-addressed model release with
weights, canonical preprocessing, recipe, loss terms/weights, seed, training
and held-out case manifests, metrics, limits, model card, and any declared ONNX
inference artifact/availability receipt. It refuses an
incomplete corpus, an inconsistent mesh/physics declaration, an unpinned
recipe/image, or fewer than the declared number of independent training and
held-out **cases**. Splitting neighbouring nodes or quadrature points from one
solve is data leakage, not a test set.

`screen` accepts a compatible declared case and returns predicted displacement
and derived, labelled quantities plus PDE/boundary residual summaries,
applicability/OOD result, model and input digests, and an explicit
`experimental` claim boundary. It refuses incompatible geometry, material,
loading, crack-pair identity, missing boundary labels, unavailable model bytes,
or out-of-domain inputs. The module hides mesh reading, collocation selection,
enrichment construction, normalization, autodiff, and ONNX export behind this
small interface.

`prepare` is the case-bound repeated-inference operation. It rechecks release
closure, declared-case compatibility, OOD envelope, and browser runtime
capability before returning a browser-safe experimental package. It is not a
general model-download operation and cannot return a package that changes
reference lifecycle, outcome, acceptance, or Field Artifact availability.

The existing `FieldSet` remains the evidence adapter: raw XDMF/HDF5 is read in
the trusted backend training implementation, never in the browser. The browser
may show a separate PINN field artifact only when its observation is available;
it must label it surrogate/experimental and never overwrite the accepted
reference field.

### PyTorch and PhysicsNeMo realization

The CMC module remains **PhysicsConstrainedSurrogate**, not a wrapper around a
PhysicsNeMo training script.  Its public interface is still exactly `release`
and `screen`.  This preserves the evidence and claim contract if the internal
runtime changes, and makes the framework a replaceable implementation detail
rather than a source of case semantics.

```text
PhysicsConstrainedSurrogate
  release(corpus, recipe) / screen(release, case)
            |
            +-- corpus and release gate
            +-- PinnProblemKernel registry     (private seam)
            +-- TrainingRuntime                (private seam)
            +-- provenance/export/evaluation

PinnProblemKernel: r0-elastic/v1, r1-cohesive/v1, ...
TrainingRuntime:    TorchRuntime, PhysicsNeMoRuntime
```

`PinnProblemKernel` is the case-specific physics adapter.  It accepts one
declared problem card, not a list of optional mechanisms.  It owns mesh
quadrature/boundary/pair-map materialisation, the output/state layout, declared
enrichment, admissibility constraints, loss and metric construction, and the
case compatibility/OOD rules.  A kernel produces an internal
`MaterializedPinnProblem`; callers do not receive raw tensors, dataloaders,
PhysicsNeMo `Domain` objects, or optimiser state.

`TrainingRuntime` consumes that materialized problem and a fully pinned recipe,
then returns weights, deterministic evaluation batches, and runtime receipts.
The first implementation must be a thin `TorchRuntime` used for the R0
manufactured-solution spike.  `PhysicsNeMoRuntime` is the second adapter and
uses the same materialized quadrature batches and loss terms.  It may use
PhysicsNeMo models, datapipes, distributed execution, and custom constraints,
but it must not replace the declared mesh with generic geometry sampling or
make its `Domain`/`Constraint` objects part of the CMC interface.  This is a
real seam only when both adapters exist; until then, keep the runtime protocol
private and do not install PhysicsNeMo merely to make a one-adapter abstraction
look fashionable.

The recipe pins the selected runtime (`torch` or `physicsnemo`), framework and
Torch distribution identities, model architecture, optimiser/scheduler,
precision/device policy, seed/determinism policy, loss-weight policy,
preprocessing, export policy, and the exact problem-card digest.  The release
records all of those identities by digest.  Framework version alone is not a
reproducibility identity.

### ONNX release artifacts and repeated browser use

ONNX is an optional **inference adapter** for a pinned `ModelRelease`; it is
neither the model's evidence of physical validity nor a replacement for the
server-side `screen` gate. A recipe declares `onnx_export` as `required`,
`best_effort`, or `disabled`. A frontend-capable release requires `required`:
export/parity failure makes that capability unavailable even if the native
runtime release remains otherwise inspectable.

The exporter emits one immutable `cmc.surrogate-onnx.v1` **InferencePackage**:

```text
InferencePackage
  manifest digest and ModelRelease digest
  model.onnx bytes + SHA-256 + ONNX opset/importer identity
  input contract: ordered names, dtypes, shapes, units, normalization digest
  output contract: ordered names, dtypes, shapes, units, reconstruction digest
  applicability fingerprint: problem-card, mesh/pair-map, material,
                             kinematic, and declared loading-envelope digests
  canonical parity vectors and tolerances; native-vs-ONNX result receipt
  runtime compatibility: required ONNX Runtime Web features and known refusal
                         reason when a browser runtime is not supported
```

The package contains no raw XDMF/HDF5, object-store path, credentials, or
accepted reference field. Its mesh/coordinate input, when needed for local
inference, is a separate browser-safe experimental projection with its own
digest. Predicted values generated from it remain `experimental` and are never
merged with `cmc.field-artifact.v1` reference evidence.

The frontend does not receive a general `model.onnx` URL and arbitrary tensors.
It calls the `prepare` operation of `PhysicsConstrainedSurrogate`; its internal
**Surrogate Inference Distribution** implementation resolves a specific release
and declared case:

```text
prepare(ModelRelease, DeclaredPinnCase, BrowserRuntimeProfile)
  -> BrowserInferencePackage | InferenceRefusal
```

This deep module hides release lookup, digest verification, problem-card
compatibility, OOD/envelope checks, browser-runtime capability selection,
byte-range/cache policy, and experimental-field projection. It refuses a stale
package, a non-ONNX release, incompatible case evidence, unsupported browser
operators, an unverifiable manifest, or a request outside the declared loading
envelope. The browser may cache bytes by content digest and re-run inference for
the already admitted package; it must not invent a case card, change mechanics
parameters, or declare a reference outcome. A locally calculated result is
display-only until a later server-owned validation workflow records it as a
separate surrogate observation.

The release pipeline exports after held-out evaluation, then executes parity on
canonical retained evaluation batches: native PyTorch/PhysicsNeMo prediction
versus ONNX Runtime on the declared export target(s). The receipt reports
per-output absolute/relative error, tolerance policy, unsupported operators,
and exact runtime identities. Do not compare only a scalar loss, and do not
publish a frontend package when its preprocessing or output reconstruction is
implemented in undocumented JavaScript. The same canonical transform bytes must
be used by the training/evaluation implementation and the ONNX package.

The rungs are accommodated through separate kernels with incompatible state
layouts where physics requires it:

| kernel | prediction/state layout | non-negotiable declared checks |
| --- | --- | --- |
| `r0-elastic/v1` | displacement; no carried state | plane-strain energy, displacement control, traction-free paired lips, opening enrichment, declared J convention |
| `r1-cohesive/v1` | displacement plus damage/history per increment | bounds, non-healing history, positive dissipation, traction-separation law, unload/reload, restart replay |
| `r2-contact/v1` | R1 state plus normal gap/pressure | gap and pressure non-negative, complementarity on paired lips |
| `r3-frictional-interface/v1` | R2 state plus tangential slip/stick state | stick/slip law, friction, frictional dissipation; effective interface claim only |
| `r4-microstructure/v1` | conditional stochastic field/operator plus ensemble state | seeded microstructure, break history, redistribution assumptions, ensemble statistics |
| `r5-thermoelastic/v1` | mechanics conditioned on declared thermal field | thermal-field identity and one-way coupling declaration |
| `r6-fatigue/v1` | recurrent or cycle-block irreversible history | R-ratio, frequency, dwell, cycle replay and history monotonicity |
| `r7-evolving-geometry/v1` | geometry evolution plus mesh-transfer state | crack-geometry identity, remeshing/transfer receipt, sensitivity studies |

This is not a promise that every rung should be a PINN.  In particular, R4 may
select a conditional stochastic operator and R7 may reject fixed-mesh neural
representations entirely.  The registry makes those selections explicit and
keeps an R0 network from silently acquiring unsupported mechanisms.

The release path is: validate accepted corpus and case-level split -> select one
kernel by problem-card key -> materialize declared evidence -> train through the
selected runtime -> evaluate only on held-out full cases -> export/verify ->
emit a digest-addressed release.  The screen path is: load pinned release ->
re-check problem-card compatibility, evidence identities, and OOD envelope ->
infer through its recorded kernel/runtime -> calculate declared residual and
metric summaries -> emit an experimental observation.  Neither path writes the
Run Mirror; its workflow adapter records the returned evidence after the fact.

The first vertical slice is deliberately smaller than a release: a native-Torch
R0 manufactured solution, mesh quadrature, paired-lip opening, energy and
traction residuals, and refusal of the current single-case corpus.  It must
produce canonical batch/provenance receipts that a later `PhysicsNeMoRuntime`
can consume unchanged.  Add PhysicsNeMo only after that spike demonstrates a
specific gain (for example distributed execution or an appropriate reusable
model/datapipe) while preserving the R0 tests and receipt identities.

### Argo placement and authority

`pinn-release` is a separate workflow family, not a task hidden inside an R0
reference attempt. It consumes a declared accepted-reference corpus and emits a
ModelRelease artifact through the same collector pattern. `pinn-screen` is an
optional final stage after reference artifact publication and only when the
case passes model-compatibility/OOD checks.

The Run Mirror records surrogate observations independently. A successful
PINN screen leaves the reference run's lifecycle, outcome, and evidence
disposition untouched; a bad, unavailable, or out-of-domain screen becomes
`indeterminate` evidence, not a reference failure. There is currently only
one accepted R0 field-export fixture, so a defensible model release is blocked
until a declared multi-case accepted corpus exists. A single-case PINN can be a
numerical experiment, but not the promised surrogate.

### Tests that cross the interface

1. A release refuses unaccepted reference artifacts, incompatible pair-map or
   material declarations, duplicate case digests, and node-level split leakage.
2. A manufactured elastic solution establishes energy, displacement, and
   traction residual calculations before reference-field fitting is attempted.
3. A paired-lip manufactured opening proves that the enrichment preserves a
   discontinuity; a smooth-only network is rejected for this case family.
4. Screening refuses an undeclared crack geometry, boundary condition, or
   out-of-domain parameter even if the model returns numbers.
5. A held-out full case reports field/energy/declared-\(J\) errors and residual
   summaries with provenance. It cannot change the reference run's outcome.
6. Export/import produces an ONNX prediction within declared numerical
   tolerance of the pinned release, or records an explicit unavailable receipt;
   a `required` frontend export cannot be distributed when unavailable.
7. Inference-package resolution refuses a changed case/pair-map/material or
   unsupported browser runtime; cached bytes with the same manifest digest
   retain the native-versus-ONNX parity result.

## Delivery order

1. Add `AttemptPlan`, the catalog, and compiler refusals with deterministic
   render tests; do not invoke Hera or Docker yet.
2. Add the Compose-equivalent adapter and stage/event/artifact parity tests.
3. Add Hera render/validation and publish the rendered-YAML receipt. Remain
   cluster-free.
4. Create R0 multi-case reference evidence and a versioned PINN problem card.
5. Implement manufactured-solution tests and `PhysicsConstrainedSurrogate`
   release refusal paths before any training loop.
6. Train/evaluate only after the corpus gate passes; export and parity-check a
   declared ONNX package, then integrate `pinn-release` and optional
   `pinn-screen` as report-only workflow families.
7. Add the browser Inference Distribution adapter only after a release has a
   verified `required` ONNX package; show it as an experimental surrogate field,
   never as an accepted Field Artifact.

## Rejected designs

- **Argo tasks writing Postgres or MinIO directly:** duplicates authority and
  gives numerical containers inappropriate credentials.
- **A generic `run_yaml` endpoint:** turns case cards, image identity, and
  retry policy into caller knowledge and defeats the compiler's depth.
- **Treating the V2 YAML sketch as runnable:** it contains placeholders and a
  malformed parameter/GPU contract, so it is historical intent only.
- **A smooth coordinate MLP over the whole domain:** it cannot reliably express
  the declared crack opening or make paired-lip correspondence auditable.
- **Training from one R0 fixture or splitting its nodes:** produces an
  impressive-looking interpolation exercise with no credible held-out case
  evidence.
- **Letting a low residual certify a fracture result:** residuals check the
  declared equation and constraints; they do not establish calibration,
  physical validity, or reference-solver acceptance.

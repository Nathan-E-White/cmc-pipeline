# V3 PINN workflow deepening

## Status and decision

This is a design-only consolidation of the selected deepening work. It adds no
dependencies, training, ONNX runtime, Argo submission, container image, or
database migration.

For the future V3 surrogate lane, the R0 crack-enriched variational PINN
replaces the earlier FNO direction. This records a planning decision, not a
claim that an FNO has been implemented or removed: `docs/v2/argo-workflow-design.yaml`
remains a non-runnable historical sketch. The reason is narrow: no declared
multi-case training corpus supports an FNO release, and R0 must retain
unstructured mesh quadrature plus paired-lip opening evidence rather than force
that evidence into an arbitrary regular grid.

The authority model is unchanged:

- Run Mirror owns admission, lifecycle, ordered events, terminal outcome, and
  artifact metadata.
- A reference Field Artifact is the only browser interpretation of accepted
  XDMF/HDF5 reference evidence.
- The PINN, ONNX package, and browser-local prediction are report-only,
  experimental surrogate evidence.
- MinIO stores immutable bytes by digest. Solver and training containers receive
  no MinIO credentials. Argo is an execution adapter, never a scheduler of
  record or a direct Postgres writer.

## Composed design

```text
Declared case + Run Mirror admission
                  |
                  v
          Workflow Compiler --------> Workflow Capability Policy (internal)
                  |                                |
                  |                                +-- Compose execution adapter
                  |                                +-- Hera/Argo execution adapter
                  v
          Typed Artifact Collector
                  |
                  +-- accepted Field Set --> Reference Field Artifact
                  |                              |
                  v                              v
          Reference Corpus Curator ------> PhysicsConstrainedSurrogate
                  |                         release / screen / prepare
                  v                              |
          frozen Corpus Receipt                 +-- model release
                                                 +-- ONNX InferencePackage
                                                 +-- experimental observation
                                                         |
                                                         v
                                       Provenance Closure Verifier
                                                         |
                                                         v
              Operational Presentation <--- Browser / Terminal adapters
```

Each **Module** has one caller-facing **Interface**. Its private implementation
may use smaller internal seams, but callers never receive a runner command,
container credential, raw XDMF/HDF5 byte, PyTorch tensor, PhysicsNeMo object,
MinIO path, or Argo client.

## 1. Workflow Compiler

### Interface

```text
compile(AttemptPlan) -> CompiledWorkflow | WorkflowRefusal
```

`AttemptPlan` is created by the Case Executor from an admitted Run Mirror
attempt. It carries run/attempt/case identity, a canonical declared case card,
a workflow key, declared input artifact receipts, requested target, and only
the retry/cancellation policy permitted by the catalog.

`CompiledWorkflow` carries a target-neutral ordered stage inventory, declared
input/output roles, immutable image identities, declared capability constraints,
and canonical rendered-workflow bytes and digest when the target supports
rendering. `WorkflowRefusal` is structured and includes invalid case card,
unknown workflow, unresolved image, unavailable capability, invalid dependency,
unsupported retry, or invalid render.

### Depth and implementation

The compiler hides catalog lookup, case-card compatibility, topological order,
target placement, image pinning, capability validation, Hera rendering, YAML
validation, and stable output identity. The current runner selection becomes a
private catalog detail; callers do not learn a growing set of runner keys,
commands, terminal policies, or Argo templates.

The compiler has two real execution **Adapters**: Compose and Hera/Argo. Their
shared target-neutral plan creates leverage and locality; the Case Executor
does not choose different commands for them.

### Workflow families

`r0-reference-field-export/v1` remains the reference family. It ends with an
executor-owned publication stage and may never allow a surrogate result to
change reference acceptance.

`pinn-release-r0/v1` is a separate family, never a hidden reference subtask:

```text
Run Mirror admit (outside workflow)
  -> corpus-attest
  -> materialize declared read-only inputs
  -> train-r0-pinn
  -> evaluate-held-out-cases
  -> export-onnx
  -> parity-check
  -> collect-model-release
```

`corpus-attest` consumes a frozen Corpus Receipt. `train-r0-pinn`, evaluation,
export, and parity receive only declared read-only inputs plus scoped scratch
space; none receives Postgres or MinIO credentials. `collect-model-release` is
the trusted collector action that validates declared output profiles, publishes
digests, and asks the Case Executor to record observations through Run Mirror.

`pinn-screen-r0/v1` is optional after reference artifact publication and only
for a declared compatible case. It emits a separate experimental observation;
it does not adjudicate the reference case.

### Interface tests

1. The same `AttemptPlan` gives identical inventory, YAML bytes, and digest.
2. Missing images, cycles, mutable tags, undeclared inputs, unavailable GPU or
   distributed capability, and hidden retry are refused before execution.
3. Compose and Hera derive the same declared stages, roles, images, and
   capability constraints.
4. Every PINN numerical stage lacks object-store and database credentials;
   collection alone publishes after profile validation.
5. A failed training/export/parity stage produces ordered experimental evidence
   and cannot alter an accepted reference Field Artifact.

## 2. PhysicsConstrainedSurrogate: release, ONNX, and browser reuse

### Interface

```text
release(CorpusReceipt, PinnRecipe) -> ModelRelease | ModelRefusal
screen(ModelRelease, DeclaredPinnCase) -> SurrogateObservation | ObservationRefusal
prepare(ModelRelease, DeclaredPinnCase, BrowserRuntimeProfile)
  -> BrowserInferencePackage | InferenceRefusal
```

This one evidence-bearing **Module** owns release, screening, and repeated
inference preparation. `prepare` is not a general model download operation. It
re-checks closure, declared case compatibility, OOD envelope, browser runtime
capability, and package identity before it returns browser-safe bytes.

The `TrainingRuntime` and `PinnProblemKernel` are private implementation seams.
Native PyTorch is the first R0 adapter; PhysicsNeMo is a later adapter that
must consume the same mesh-quadrature materialization and loss terms. Do not
make tensors, DataPipes, `Domain`, `Constraint`, optimizer state, or ONNX
Runtime implementation part of this Module's Interface.

`ModelRelease` contains weights, problem-card and recipe digests, canonical
transforms, held-out metrics, limits, model card, and an ONNX availability
receipt. For a frontend-capable recipe, ONNX export is `required`; unavailable
export/parity leaves the native release inspectable but refuses browser reuse.

`BrowserInferencePackage` contains a `cmc.surrogate-onnx.v1` manifest, pinned
ONNX bytes, ordered input/output names, shapes, dtypes, units, transform
digests, compatibility fingerprint, parity receipt, browser runtime
requirements, and an optional browser-safe experimental mesh/coordinate
projection. It contains no accepted reference field, raw solver file, object
path, or credential. Browser caching is by manifest/content digest only.

### Interface tests

1. A release refuses an incomplete corpus, duplicate/full-case split leakage,
   incompatible mesh/pair-map/material, and unpinned recipe/runtime.
2. A paired-lip manufactured R0 field retains opening across the declared
   crack; a smooth-only representation is refused for this problem card.
3. Native and ONNX outputs meet declared per-output parity tolerances on
   retained canonical batches, or the explicit unavailable receipt is returned.
4. `prepare` refuses changed input evidence, OOD parameters, an unsupported
   browser runtime, or broken provenance closure.
5. Browser-local inference remains experimental and has no path to reference
   lifecycle, acceptance, or Field Artifact mutation.

## 3. Operational Presentation

### Interface

```text
present(run_id, detail_cursor?) -> OperationalView | PresentationUnavailable
```

Operational Presentation is the sole interpreter for selected-run facts. It
joins compact Run Mirror records, Field Artifact availability, Workflow Compiler
receipts, and surrogate observations into one bounded `OperationalView`.
Browser and terminal are adapters over the same view. Neither queries Docker,
Argo, MinIO, or Postgres independently.

The reference lane remains primary. The surrogate lane distinguishes
`corpus-blocked`, `queued`, `evaluating`, `experimental`, `out-of-domain`, and
`unavailable`. ONNX availability appears only as a reasoned experimental
capability for the declared compatible case; it is never a reference status,
progress estimate, or confidence dial.

### Interface tests

1. Browser and terminal see identical state words, reasons, digests, and
   bounded evidence pages.
2. Hera `rendered`/`validated` cannot display as submitted or executed.
3. Cached browser inference cannot display as a Run Mirror event until a
   later trusted workflow records an observation.
4. A workflow success beside reference `indeterminate` preserves that
   distinction visibly.

## 4. Typed Artifact Collector profiles

### Interface

```text
collect(DeclaredOutputSet) -> ArtifactSetReceipt | PublicationRefusal
```

The collector is one deep Module that hides scoped-output containment, manifest
parsing, role declaration, digesting, byte publication, media-type checks, and
profile validation. It has private artifact-profile implementations; a runner
or workflow never supplies an arbitrary validation callback.

Profiles are declared in the Workflow Catalog:

| profile | required evidence | claim constraint |
| --- | --- | --- |
| `reference-field/v1` | field-set manifest, XDMF, HDF5, acceptance evidence, usable projection | may support accepted Field Artifact only |
| `reference-corpus/v1` | frozen member list, full-case split, eligibility/refusal evidence | never decides reference lifecycle |
| `model-release/v1` | recipe/runtime, weights, metrics, held-out manifest, model card | experimental only |
| `surrogate-onnx/v1` | ONNX bytes, contracts, transforms, parity receipt, browser requirements | reusable experimental inference only |
| `surrogate-observation/v1` | declared compatible input, predicted projection, residual summaries | never overwrites reference field |

The profile controls what an artifact means; MinIO only owns bytes and Run
Mirror only records artifact metadata/lifecycle observations. This separation
keeps the collector deep without making it an alternate authority.

### Interface tests

1. A role absent from its profile, path traversal, duplicate role, digest
   mismatch, or malformed required bytes is refused before publication.
2. A valid ONNX blob without transforms/parity cannot satisfy
   `surrogate-onnx/v1`.
3. Reference-field acceptance still requires usable XDMF/HDF5 evidence, not
   merely a successful numerical container.

## 5. Reference Corpus Curator

### Interface

```text
freeze(CorpusRequest) -> CorpusReceipt | CorpusRefusal
```

This Module selects accepted reference Field Sets and freezes membership before
the model release workflow begins. It owns eligibility, duplicate detection,
case-level split assignment, problem-card and mesh/pair-map compatibility, and
corpus provenance. It does not train, execute a workflow, publish bytes, or
decide any reference lifecycle/outcome.

R0 and later problem cards justify real internal adapters: each can define its
own eligible case family and compatibility checks, while callers always receive
one immutable `CorpusReceipt`. A later accepted reference run cannot change an
already frozen receipt.

### Interface tests

1. One accepted R0 field set refuses release because the declared independent
   training/held-out full-case cardinality is not met.
2. Node/quadrature split leakage, duplicate case digest, unaccepted member,
   changed pair-map/material/problem card, and mutable membership are refused.
3. Receipt membership, split, and digest remain stable after more runs arrive.

## 6. Provenance Closure Verifier

### Interface

```text
verify(DeclaredArtifactRoot) -> ProvenanceClosure | ClosureRefusal
```

The verifier resolves a declared root artifact and checks typed, transitive
edges: accepted Field Set to Corpus Receipt, Corpus Receipt to recipe/problem
card/runtime, release to ONNX parity package, and observation/projection to its
compatible input. It returns a compact closure or structured refusal to the
surrogate Module, collector, Operational Presentation, and browser preparation.

It is not a second object store, registry, scheduler, or lifecycle ledger.
Postgres and MinIO retain their existing authorities. The verifier concentrates
graph semantics so every consumer reaches the same answer.

### Interface tests

1. Missing/changed ancestor, undeclared edge, profile-version mismatch, cycle,
   missing parity receipt, or incompatible root is refused.
2. Equivalent declared graphs give stable closure identity.
3. A valid ONNX byte digest with broken corpus/release lineage is refused.

## 7. Workflow Capability Policy (internal)

Capability policy belongs inside the Workflow Compiler implementation. It maps
declared stage requirements—CPU/GPU class, distributed execution, precision,
network, scratch, read-only input, and credential prohibition—to each target.
It gives one compiler result for Compose and Hera; do not expose a new public
module until a third independently varying execution adapter exists.

The policy must refuse a target whose declared capability cannot be supplied.
It must never downgrade a GPU/distributed/credential constraint silently. Its
tests are compiler interface tests, not a separate test hierarchy.

## 8. Hera/Argo ML workflow adapter

Hera/Argo is a Workflow Compiler adapter, not a workflow definition language
callers write directly. In this delivery, its observable product is canonical
rendered YAML plus validation receipt. It does not submit to a cluster.

For `pinn-release-r0/v1`, rendering must show declared stage dependencies,
immutable images, mounted or staged read-only inputs, scoped scratch outputs,
capability requirements, and the collector-only publication stage. It must not
render a task that writes Run Mirror rows, uploads directly to MinIO, or decides
reference acceptance. A later submit/observe adapter remains behind the same
workflow-execution seam and reports facts through Case Executor.

## 9. Argo Workflow submission and execution (later slice)

This section designs a later cluster-execution slice. It does not authorize a
cluster, credentials, RBAC changes, workflow submission, or a claim that a
rendered workflow ran. The current Hera output remains a rendered/validated
receipt only.

### Workflow Execution interface

`WorkflowExecution` is the execution seam already justified by two adapters:
the Compose-equivalent adapter and the later Argo adapter. It has three
operations because submit, observation, and cancellation have different durable
facts and error modes:

```text
submit(CompiledWorkflow, ExecutionGrant) -> WorkflowSubmission | ExecutionRefusal
observe(WorkflowSubmission, observation_cursor?)
  -> WorkflowObservationPage | ObservationRefusal
request_cancel(WorkflowSubmission) -> CancellationRequestReceipt | ExecutionRefusal
```

`ExecutionGrant` is minted only after Case Executor claims an admitted Run
Mirror attempt. It carries immutable run/attempt/case/workflow identities, a
submission idempotency key, permitted namespace, and declared target
capabilities. It is not a Kubernetes credential or free-form YAML authority.

`submit` records the exact compiled-workflow digest and returns the namespace,
generated workflow name, Kubernetes UID, submitted-at fact, and initial
resource-version cursor. Retrying the same grant returns the original receipt
only when its workflow digest is identical; a digest/name/attempt mismatch is
refused. The full case card, raw paths, credentials, and unbounded logs do not
become Kubernetes labels or annotations. Labels carry only constrained CMC
identity values needed for selection; full identities stay in the Run Mirror
receipt.

`observe` converts Argo node/workflow facts into a bounded, ordered page of
stage observations. Its cursor is opaque and includes the last accepted
resource-version/node transition identity. It deduplicates relists, reconnects,
and terminal snapshots before handing observations to Case Executor, which alone
appends Run Mirror events. An Argo `Succeeded`/`Failed`/`Error` status is an
execution fact; it is never a CMC numerical outcome or accepted Field Artifact.

`request_cancel` forwards only a Run Mirror `cancel-requested` fact. The first
policy uses Argo's workflow shutdown `Stop` behaviour so exit handling can run;
it returns a forwarding receipt, not `cancelled`. A separate, explicitly
authorized escalation policy would be required before an Argo `Terminate`
request is allowed. Only subsequent cluster observation lets Case Executor and
Run Mirror record a terminal cancellation outcome.

This shape gives callers leverage: they learn one execution interface, while
the implementation hides Hera client construction, Kubernetes authentication,
workflow naming, resource-version watching, status normalisation, retry-safe
submission, shutdown patching, and transport recovery. The interface is the
test surface.

### Argo adapter implementation and authority

`ArgoWorkflowExecution` is the adapter that uses Hera for object construction
and a pinned Argo/Kubernetes transport for create/get/watch/patch operations.
Hera is not the authority and must not be allowed to block the executor waiting
for a terminal workflow: submission returns after the cluster acknowledges
creation, and observation proceeds through bounded resumable polls or watches.
This avoids turning one backend worker into an unbounded Argo wait loop.

The adapter runs in a dedicated workload namespace, separate from the Argo
controller namespace. The submitter identity receives only namespace-scoped
workflow create/read/list/watch and the narrow patch needed for declared
shutdown; it does not receive Pod, Secret, ConfigMap, PVC, or cluster-wide
write privilege. The workload identity is a dedicated numerical service account
with only the minimum Argo executor permissions needed for its pinned Argo
version. It receives no Postgres DSN, MinIO credential, broad cloud credential,
or elevated Kubernetes role. Pod security settings are declared by the catalog,
including non-root execution and only the mounts each stage needs.

Creating a Workflow can create Pods, so RBAC alone does not make a broadly
programmable workflow safe. Submission therefore targets a namespace-scoped,
reviewed workflow-template/catalog identity whenever the graph is static; a
dynamic compiled workflow requires a Kubernetes admission policy that checks
the CMC compiler identity, immutable image digests, allowed service accounts,
mounts, and workflow labels before creation. The Workflow Compiler remains the
place that decides whether a compiled plan is admissible.

### Inputs, outputs, and logs

The adapter provisions a per-attempt execution workspace with separate declared
read-only inputs and writable scratch outputs. A trusted input materializer may
receive short-lived, object-specific read capability to place digest-verified
inputs in that workspace. Training, FEM, evaluation, export, and parity pods
receive the mounted inputs but no object-store credentials.

The terminal collector is the only stage allowed narrow output-publication
capability. It validates the Typed Artifact Collector profile in a scoped output
area, publishes immutable digests, and returns declared receipts to Case
Executor. It runs on successful completion and through the declared exit path
on failure/cancellation, but incomplete artifacts remain unavailable or
indeterminate according to their profile. An Argo artifact repository is not a
substitute for the collector: it would make generic workflow artifact handling
look like CMC evidence authority.

Argo archive status and logs are operational aids only. Do not treat Argo's
workflow archive as the CMC event ledger, and do not use automatic Argo log
archival as the normal CMC evidence path. Raw logs, when retained under a
separate declared policy, remain scoped diagnostic artifacts; Operational
Presentation exposes bounded evidence summaries and exact reasons instead.

### R0 PINN execution graph

```text
Run Mirror admit / Case Executor claim         (trusted backend, outside Argo)
                    |
                    v
Argo submit + workflow receipt                 (ArgoWorkflowExecution)
                    |
                    v
corpus-attest -> input-materialize -> train-r0-pinn
                                      -> held-out-evaluate
                                      -> export-onnx -> parity-check
                                                         |
                                                         v
                                               collect-model-release
                                                         |
                                                         v
Case Executor records observations / collector receipts -> Run Mirror
```

The `pinn-screen-r0/v1` graph is separate and optional after accepted reference
artifact publication. It may materialize a declared compatible input, run
screening, and collect an experimental observation. It has no edge that can
change the reference attempt's lifecycle, outcome, or accepted Field Artifact.

### Interface tests and cluster admission proof

1. An in-memory Argo adapter and a transport-contract fake prove idempotent
   submission, digest mismatch refusal, observation de-duplication, reconnect
   cursor handling, and `Stop` forwarding without a cluster.
2. The same compiled stage inventory produces identical Compose and Argo
   declared roles, images, capability constraints, and collector placement.
3. Rendered RBAC/workflow documents prove that numerical pods lack Postgres,
   MinIO, broad cloud, Secret-reading, and elevated Pod permissions; collector
   and input materializer capabilities are separately scoped.
4. A controlled test cluster proves creation acknowledgement, watch/relist
   recovery, stage observation ordering, and cancellation observation. It does
   not turn a submitted workflow into reference acceptance evidence.
5. A failure before collector publication, collector profile refusal, and a
   cancelled workflow leave the reference Field Artifact unavailable or
   unchanged and preserve inspectable Run Mirror facts.

### Official framework constraints

Argo documents that workflow users minimally create/read Workflows and that
Workflow creation can create arbitrary Pods unless workflow restrictions are
used; workflow Pods use the declared service account, and a dedicated service
account is recommended over the namespace default. Argo also documents the
minimal executor RBAC for supported versions and that `shutdown` is a workflow
field. Hera can render YAML or create a workflow, but its wait methods poll for
terminal completion, which the CMC adapter deliberately does not expose as
backend control flow. See [Argo security](https://argo-workflows.readthedocs.io/en/latest/security/),
[workflow RBAC](https://argo-workflows.readthedocs.io/en/release-3.4/workflow-rbac/),
[workflow fields](https://argo-workflows.readthedocs.io/en/latest/fields/), and
[Hera workflow methods](https://hera.readthedocs.io/en/stable/api/workflows/workflow_classes/workflow/).

## Delivery sequence

1. Deepen the executor into Workflow Compiler plus Compose adapter, with
   deterministic compile/refusal tests. Quarantine the historical FNO YAML;
   do not use it as a template.
2. Replace callback-style publication rules with the Typed Artifact Collector
   and preserve the current `reference-field/v1` negative tests.
3. Add Corpus Curator and Provenance Closure Verifier refusal paths. The current
   single R0 fixture must remain corpus-blocked.
4. Add R0 manufactured-solution PyTorch tests and the private native runtime;
   establish paired-lip, energy, and traction evidence before training.
5. Add `pinn-release-r0/v1` Compose-equivalent stages through the compiler;
   train only after a valid frozen corpus exists.
6. Add ONNX export/parity and `prepare` with an in-memory browser-runtime
   adapter; no frontend dependency or UI yet.
7. Add Operational Presentation and browser/terminal adapters over its one
   view; then surface experimental ONNX use when a compatible release exists.
8. Add Hera render/validation parity for the same workflow plan. Submission or
   cluster execution remains a later separately authorized slice.
9. Only after a separate cluster/RBAC authorization, implement the Argo
   `WorkflowExecution` adapter with in-memory transport tests before a
   controlled test-cluster proof.

## Deliberate non-modules

- No generic fracture-mechanism flags: R0--R7 retain separate problem cards and
  physics kernels.
- No separate ML lifecycle ledger: that would duplicate Run Mirror authority.
- No public PyTorch/PhysicsNeMo/ONNX Runtime seam: those are implementation
  details beneath the surrogate Module.
- No browser access to raw model URL plus arbitrary tensors: `prepare` returns
  only a declared compatible experimental package.
- No Argo task direct Postgres/MinIO writer: collection and Run Mirror recording
  remain trusted backend actions.
- No Argo `Succeeded`/`Failed` state promoted directly to a CMC numerical
  outcome: execution observation and reference acceptance remain distinct.

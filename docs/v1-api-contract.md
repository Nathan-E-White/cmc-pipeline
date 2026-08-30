# V1 fixture-backed API contract

## Status and boundary

This document defines the V1 HTTP/JSON boundary for the CMC Fracture Pipeline.
V1 serves a small, versioned fixture corpus so that the UI and the later
backend adapter can be developed against stable data. Its retrieval routes
serve fixture data; its declared fixture workflow commands may create only
in-memory fixture run and verification records. V1 does **not** invoke an
external job, run a finite-element solver, load a learned model, or establish
a material or flight-readiness claim. Those activities require a separately
reviewed execution and evidence path; the Argo file is explicitly a
[non-runnable V2 design](v2/argo-workflow-design.yaml).

Terminology follows the project [context](../CONTEXT.md). In particular, a
`reference_solution` is a numerical comparison authority for its declared
model and configuration, and an `adjudication` is a recorded comparison with
declared criteria. Neither term means experimental truth or qualified
structural prediction.

## Common conventions

- Base path: `/api/v1`.
- Representation: JSON (`application/json; charset=utf-8`).
- Identifiers are opaque ASCII slugs. Clients must not infer material,
  configuration, or result status from an identifier.
- Every successful response contains `api_version: "v1"`, a `fixture` object,
  and a `provenance` object. Clients should display the supplied labels rather
  than manufacture stronger claims from the numeric fields.
- The case-retrieval routes in this document allow `GET` and `HEAD`; an
  unsupported method returns `405 method_not_allowed` with that route's
  `Allow` header. Declared fixture workflow commands use `POST` and describe
  their own request and response semantics.
- This specification defines payload shape and semantics. It does not yet
  authorize CORS, authentication, caching policy, persistence, or a deployed
  service.

### Shared fixture and provenance fields

```json
{
  "api_version": "v1",
  "fixture": {
    "corpus_id": "v1-demo-2026-08",
    "case_id": "sic-sic-panel-042",
    "revision": "1",
    "kind": "representative"
  },
  "provenance": {
    "source_kind": "fixture",
    "reference_solution": {
      "model_id": "demo-cmc-fracture-model",
      "solver_configuration_id": "demo-config-r1",
      "discretization_id": "demo-mesh-r1"
    },
    "claim_boundary": "Comparison evidence within the declared numerical model; not experimental truth or a qualified structural prediction."
  }
}
```

`fixture.kind` is always `representative` in V1. `reference_solution` records
the comparison context, not an assertion that the server executed a solver.

## Routes

### `GET /api/v1/cases`

Lists the cases included in the fixture corpus. The list is the discovery
mechanism for a client; clients must not hard-code a case list from this
document.

```json
{
  "api_version": "v1",
  "fixture": { "corpus_id": "v1-demo-2026-08", "kind": "representative" },
  "provenance": { "source_kind": "fixture", "claim_boundary": "Representative fixture metadata only." },
  "cases": [
    {
      "case_id": "sic-sic-panel-042",
      "label": "SiC/SiC panel 042",
      "architecture": "sic_sic",
      "availability": {
        "adjudication": "available",
        "mesh": "available"
      }
    }
  ]
}
```

`availability` is a statement about fixture records, not the state of a live
simulation.

### `GET /api/v1/cases/{case_id}`

Returns the declared inputs and stable display metadata for one fixture case.

```json
{
  "api_version": "v1",
  "fixture": {
    "corpus_id": "v1-demo-2026-08",
    "case_id": "sic-sic-panel-042",
    "revision": "1",
    "kind": "representative"
  },
  "provenance": {
    "source_kind": "fixture",
    "reference_solution": {
      "model_id": "demo-cmc-fracture-model",
      "solver_configuration_id": "demo-config-r1",
      "discretization_id": "demo-mesh-r1"
    },
    "claim_boundary": "Comparison evidence within the declared numerical model; not experimental truth or a qualified structural prediction."
  },
  "case": {
    "label": "SiC/SiC panel 042",
    "architecture": "sic_sic",
    "inputs": {
      "coating_shear_limit_mpa": 60.0,
      "mechanical_load_kn": 45.0,
      "thermal_gradient_c_per_mm": 120.0
    }
  }
}
```

All quantities use the units encoded in their field names. The inputs are
declared fixture inputs, not operator-adjustable requests to run analysis.

### `GET /api/v1/cases/{case_id}/mesh`

Returns a compact visualisation mesh. It is a rendering artifact, not a
solver-grade mesh or a topology suitable for engineering calculation.

```json
{
  "api_version": "v1",
  "fixture": { "corpus_id": "v1-demo-2026-08", "case_id": "sic-sic-panel-042", "revision": "1", "kind": "representative" },
  "provenance": {
    "source_kind": "fixture",
    "reference_solution": { "model_id": "demo-cmc-fracture-model", "solver_configuration_id": "demo-config-r1", "discretization_id": "demo-mesh-r1" },
    "claim_boundary": "Rendering fixture only; not a solver-grade mesh."
  },
  "mesh": {
    "coordinate_system": "case_local_cartesian_mm",
    "node_count": 640000,
    "vertex_positions_mm": [-1.5, 0.0, 0.0, -1.45, 0.1, -0.02],
    "fiber_indices": [[0, 1, 2]]
  }
}
```

`vertex_positions_mm` is a flat array of XYZ triples; its length is divisible
by three. Each `fiber_indices` member is a list of zero-based indices into
that array. `node_count` is contextual metadata and need not equal the number
of rendering vertices.

### `GET /api/v1/cases/{case_id}/adjudication`

Returns the recorded fixture comparison. This is the only V1 route that may
report an acceptance outcome, and its outcome is scoped to the declared
criterion and provenance.

```json
{
  "api_version": "v1",
  "fixture": { "corpus_id": "v1-demo-2026-08", "case_id": "sic-sic-panel-042", "revision": "1", "kind": "representative" },
  "provenance": {
    "source_kind": "fixture",
    "reference_solution": { "model_id": "demo-cmc-fracture-model", "solver_configuration_id": "demo-config-r1", "discretization_id": "demo-mesh-r1" },
    "surrogate": { "model_id": "demo-fno-r1", "domain_id": "demo-domain-r1" },
    "claim_boundary": "Fixture adjudication only; not independent physical validation or qualification."
  },
  "adjudication": {
    "status": "accepted",
    "quantity": "j_integral_proxy",
    "reference_value": 12.4,
    "surrogate_value": 12.1,
    "relative_error": 0.0242,
    "acceptance_criterion": { "maximum_relative_error": 0.05 },
    "units": "J/m²"
  }
}
```

`status` is one of `accepted`, `rejected`, or `indeterminate`.

- `accepted` means the fixture’s stated criterion was met within its declared
  domain. It does not promote the surrogate to a solver replacement.
- `rejected` means the recorded comparison did not meet the criterion.
- `indeterminate` means that domain, quality, or comparison evidence was
  insufficient for an accepted screening result. A client must not render it
  as a warning-level pass.

`relative_error` is `abs(surrogate_value - reference_value) / abs(reference_value)`.
If the reference value is zero, the response instead supplies `relative_error:
null` and a `comparison_note`; the fixture cannot silently divide by zero and
pretend this is progress.

### `POST /api/v1/reference-runs`

Creates an in-memory record for a declared fixture reference run. The supplied
`case_id` and `inputs` must exactly match a fixture case; this does not submit
an external job or execute a solver.

```json
{
  "case_id": "sic-sic-panel-042",
  "inputs": {
    "coating_shear_limit_mpa": 60.0,
    "mechanical_load_kn": 45.0,
    "thermal_gradient_c_per_mm": 120.0
  }
}
```

It returns `202 Accepted` with a `run` containing an opaque `run_id`, the
declared `case_id`, and `status: "queued"`. The record exists only for the
server lifetime. V1 has no cancellation, retry, or resubmission operation.

### `GET /api/v1/reference-runs/{run_id}`

Returns the submitted record. For the deterministic V1 fixture runner, the
first status observation advances a queued record to `complete`; no wall-clock
delay or background solver is implied. Unknown IDs return `404
reference_run_not_found`.

### `GET /api/v1/reference-runs/{run_id}/results`

Returns the versioned representative reference result for a completed run:

```json
{
  "result": {
    "quantity": "j_integral_proxy",
    "value": 12.4,
    "units": "J/m²"
  }
}
```

A non-terminal record returns `409 reference_run_not_complete`; a case without
a result fixture returns `404 artifact_not_available`. A result is numerical
comparison evidence within its declared model, not experimental truth.

### `POST /api/v1/simulation/verify`

Creates an in-memory fixture comparison record against a completed reference
run. `inputs` must match the run’s declared fixture inputs. The observation
contains its `quantity`, numeric `value`, and `units`; it may declare
`domain_status: "outside_declared_domain"`.

```json
{
  "reference_run_id": "run-0001",
  "inputs": {
    "coating_shear_limit_mpa": 60.0,
    "mechanical_load_kn": 45.0,
    "thermal_gradient_c_per_mm": 120.0
  },
  "observation": {
    "quantity": "j_integral_proxy",
    "value": 12.1,
    "units": "J/m²"
  }
}
```

It returns `201 Created` with an opaque `verification_id` and a fixture
comparison whose status is `accepted`, `rejected`, or `indeterminate`.
`accepted` and `rejected` use the declared relative-error criterion. An
out-of-domain observation is `indeterminate`, has `relative_error: null`, and
contains a `comparison_note`; it is not a warning-level pass.

### `GET /api/v1/simulation/verifications/{verification_id}`

Returns a verification record during the server lifetime. Unknown IDs return
`404 verification_not_found`; a server restart intentionally removes these
in-memory records.

## Error response

All errors use this envelope:

```json
{
  "api_version": "v1",
  "error": {
    "code": "case_not_found",
    "message": "No fixture case exists for the supplied identifier.",
    "request_id": "req_01j..."
  }
}
```

`request_id` is optional until the service has request tracing. If present, it
is opaque and may be supplied to an operator for diagnosis.

| HTTP status | `error.code` | Meaning |
| --- | --- | --- |
| 400 | `invalid_case_id` | The path identifier is syntactically invalid. |
| 404 | `case_not_found` | No fixture case has that identifier. |
| 404 | `artifact_not_available` | The case exists but lacks the requested fixture artifact. |
| 404 | `reference_run_not_found` | No submitted fixture reference run has that ID. |
| 404 | `verification_not_found` | No in-memory verification record has that ID. |
| 405 | `method_not_allowed` | The addressed resource does not allow the method. |
| 406 | `not_acceptable` | The client did not accept JSON. |
| 409 | `reference_run_not_complete` | A result or verification requires a completed run. |
| 422 | `input_mismatch` | Declared input values do not match the fixture case or run. |
| 422 | `invalid_reference_run` / `invalid_verification` / `invalid_observation` | The command request lacks required declared fields. |
| 500 | `fixture_integrity_error` | The fixture corpus is inconsistent or cannot be read. Do not substitute invented values. |

For all 4xx and 5xx responses, clients must preserve the distinction between
missing evidence and an empty result. In particular, `artifact_not_available`
and `fixture_integrity_error` are not an empty mesh or an `indeterminate`
adjudication.

## Compatibility and fixture evolution

The `/v1` path fixes field meaning, not the size of a corpus. Additive fields
and additional cases are permitted. Removing or changing a required field,
changing units, or redefining an outcome requires `/v2`.

A fixture revision changes when any declared input, artifact, comparison value,
criterion, or provenance identifier changes. A client may cache a response only
when its cache key includes at least `corpus_id`, `case_id` where applicable,
and `revision`. V1 provides no live-results freshness claim.

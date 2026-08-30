# V1 development and boundaries

## Run locally

Use two terminals. The backend serves the V1 fixture API on port 8000:

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/uvicorn app.main:app --reload --port 8000
```

The frontend runs on port 3000 and proxies `/api` to that backend:

```sh
cd frontend
bun install
bun run dev
```

Run the delivery checks before treating a change as complete:

```sh
cd backend && .venv/bin/python -m pytest && .venv/bin/ruff check app tests
cd frontend && bun run test && bunx tsc --noEmit && bun run check && bun run build
```

## What V1 demonstrates

V1 serves versioned representative fixtures and keeps submitted reference-run
and verification records only in memory for one server lifetime. The browser's
surrogate observation is a declared deterministic fixture value; it does not
load or execute ONNX. `accepted`, `rejected`, and `indeterminate` are fixture
comparison outcomes within declared criteria, not physical validation, solver
qualification, flight readiness, or operational decision authority.

The route shapes, error semantics, and provenance labels are defined by the
[V1 API contract](v1-api-contract.md). Clients must display those labels rather
than infer a stronger claim from numerical values or a successful HTTP response.

## V2 seams, not V2 implementation

The [Argo workflow design](v2/argo-workflow-design.yaml) is a non-runnable
design sketch. Its image references use `registry.example.invalid` deliberately:
they are placeholders, not a registry, credential, or cluster configuration.
It has no V1 execution or deployment authority.

When V2 has an approved execution path, introduce a concrete Hera/Argo adapter
behind the existing reference-run caller-facing interface. Do not expose
workflow-shaped APIs to the UI, and do not add an abstraction hierarchy before
there is a second real adapter to support. That adapter needs its own reviewed
credentials, artifact provenance, execution lifecycle, failure policy, and
deployment evidence.

Likewise, replace the frontend's deterministic surrogate fixture only with a
small ONNX executor adapter after a model artifact, declared input/output
contract, supported runtime, domain policy, and verification evidence exist.
Until then, the fixture is intentionally mundane. In engineering this is often
preferable to an impressive-looking claim with no balance sheet behind it.

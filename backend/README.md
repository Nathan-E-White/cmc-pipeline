# Fixture API development

Create a project-local virtual environment and install the declared test tools:

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
```

Run the HTTP contract tests and lint checks from this directory:

```sh
.venv/bin/python -m pytest
.venv/bin/ruff check app tests
```

For local browser development, serve the explicitly fixture-backed API on port
8000:

```sh
.venv/bin/uvicorn app.main:app --reload --port 8000
```

This service only serves V1 representative fixture records. Its boundaries are
defined in [`../docs/v1-api-contract.md`](../docs/v1-api-contract.md).

## V3 local persistence slice

V3's Run Mirror is separate from the V1 fixture routes. Its Postgres schema,
idempotency, ordered events, and MinIO artifact identity are defined in
[`../docs/v3-run-mirror-contract.md`](../docs/v3-run-mirror-contract.md).
Compose applies each numbered migration once through the `migrate` module, so an
existing local Postgres volume receives later V3 migrations without a reset.
Run the local Compose contract tests only after `docker --context orbstack
compose up -d` has made Postgres and MinIO healthy:

```sh
CMC_RUN_MIRROR_DSN=postgresql://cmc:local-development-only@localhost:5433/cmc_pipeline \\
CMC_ARTIFACT_ENDPOINT=localhost:9000 \\
CMC_ARTIFACT_ACCESS_KEY=cmc-local \\
CMC_ARTIFACT_SECRET_KEY=local-development-only \\
.venv/bin/python -m pytest tests/test_run_mirror_contract.py
```

### V3 serial executor

The `executor` Compose service claims one queued V3 attempt at a time, invokes
only the declared `reference-solver` runner, validates its artifact manifest,
and publishes declared bytes to MinIO through the Run Mirror. It uses the host
Docker socket to launch the runner container; enable it only for this trusted
local-development composition:

```sh
docker --context orbstack compose up -d executor
```

An HTTP submission is picked up automatically. The current runner executes
`verify-case`, so an exit code of zero is recorded as a completed verification
with an `indeterminate` numerical outcome; it must not be read as a solved
physical case. Exercise the declared container path directly with:

```sh
CMC_RUN_MIRROR_DSN=postgresql://cmc:local-development-only@localhost:5433/cmc_pipeline \\
CMC_ARTIFACT_ENDPOINT=localhost:9000 \\
CMC_ARTIFACT_ACCESS_KEY=cmc-local \\
CMC_ARTIFACT_SECRET_KEY=local-development-only \\
.venv/bin/python ../scripts/v3-e2e.py
```

For the complete local workflow, frontend proxy arrangement, fixture/provenance
limits, and V2 seam notes, see [`../docs/v1-development.md`](../docs/v1-development.md).

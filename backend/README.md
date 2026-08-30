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

For the complete local workflow, frontend proxy arrangement, fixture/provenance
limits, and V2 seam notes, see [`../docs/v1-development.md`](../docs/v1-development.md).

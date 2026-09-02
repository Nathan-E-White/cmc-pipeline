# CMC Pipeline browser applications

`frontend/` is the Bun workspace and dependency-management root; it renders no
browser application. The independently deployable applications are:

- `monitor/` — operational Run Mirror observation, including Electric Shapes and resumable SSE notices, on port 3000.
- `app/` — post-run browser-safe physics results and V1 fixture controls, on port 3002.

From this directory, install once and run either application independently:

```sh
bun install
bun run dev:monitor
bun run dev:app
```

Both proxy `/api` to the local FastAPI backend. Only the monitor proxies
`/electric`. The results app receives the browser-safe `PhysicsResultView`; it
does not receive raw XDMF/HDF5, object-store paths, or an ONNX inference result.
Set `CMC_PHYSICS_APP_ORIGIN` when building the monitor image for a non-local
results-app origin.

```sh
bun run test
bun run check
bun run build:monitor
bun run build:app
```

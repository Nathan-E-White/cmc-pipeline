# Local reference-solver container

This is the local execution foundation for the CMC fracture reference path.
It deliberately stops at a generated and audited mesh. It does not execute a
reference solution, calculate a J-integral, or make a material or design claim.

## Build and smoke test

```sh
docker --context orbstack build --tag cmc-reference-solver:test --file containers/solver.Dockerfile .
bash reference/tests/reference_container_test.sh
```

The Dockerfile pins the official DOLFINx multi-architecture manifest by digest.
It installs Gmsh and its C++ headers, builds the C++20 `mesh-audit` executable,
runs its CTest suite, then runs the exact public `verify-case` command while
building the image.

## Public command

```sh
docker --context orbstack run --rm -v "$(pwd)/reference/runs:/artifacts" \
  cmc-reference-solver:test verify-case --output /artifacts
```

The command writes:

- `edge-cracked-plate-v1.msh`: quadratic Gmsh mesh;
- `mesh-audit.json`: mesh bounds, entity counts, and required physical groups;
- `environment.json`: Gmsh/DOLFINx runtime versions and the current claim boundary.

The `.geo` file intentionally has an embedded `crack_trace`, not two crack
faces. The later reference-solution slice must introduce a real discontinuity
before it may compute a J-integral. This is a guardrail, not a missing label.

`mesh-audit` is intentionally hard-coded to `edge-cracked-plate-v1`; it checks
that case's physical entities, dimensions, crack trace, quadratic triangles,
and minimum mesh quality. Before the runner supports a second case, replace
those literals with an explicit audit-contract input rather than accumulating
case-specific branches.

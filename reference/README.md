# Local reference-solver container

This is the local execution foundation for the CMC fracture reference path.
It executes one fixed, isotropic, linear-elastic plane-strain reference solve
on a generated and audited mesh. It does not yet calculate a J-integral or
make a material, validation, qualification, or design claim.

## Build and smoke test

```sh
docker --context orbstack build --tag cmc-reference-solver:test --file containers/solver.Dockerfile .
bash reference/tests/reference_container_test.sh
```

The Dockerfile pins the official DOLFINx multi-architecture manifest by digest.
It installs Gmsh and its C++ headers, builds the C++20 `mesh-audit` executable,
runs its CTest suite, then runs both public commands while building the image,
including a real plane-strain solve.

## Public command

```sh
docker --context orbstack run --rm -v "$(pwd)/reference/runs:/artifacts" \
  cmc-reference-solver:test solve-case --output /artifacts
```

The command writes:

- `edge-cracked-plate-v1.msh`: quadratic Gmsh mesh;
- `mesh-audit.json`: mesh bounds, entity counts, and required physical groups;
- `environment.json`: Gmsh/DOLFINx runtime versions and the current claim boundary.
- `displacement.xdmf`: the solved displacement field;
- `solution-summary.json`: fixed model values and a bounded solve summary.

The generator uses Gmsh's Crack plugin to turn the declared `crack_trace` into
two topologically separate `crack_faces`; `mesh-audit` rejects a mesh that
lacks that opened topology. The next closure item is domain-integral J
convergence; the present solve must not be presented as a J result.

`mesh-audit` is intentionally hard-coded to `edge-cracked-plate-v1`; it checks
that case's physical entities, dimensions, crack trace, quadratic triangles,
and minimum mesh quality. Before the runner supports a second case, replace
those literals with an explicit audit-contract input rather than accumulating
case-specific branches.

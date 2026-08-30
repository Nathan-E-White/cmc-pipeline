# Local reference-solver container

This is the local execution foundation for the CMC fracture reference path.
It executes the declared fixed, isotropic, linear-elastic plane-strain reference
benchmark on generated and audited meshes, including a bounded domain-integral
fracture quantity convergence run. It makes no CMC calibration, physical
validation, qualification, or design claim.

## Build and smoke test

```sh
docker --context orbstack build --tag cmc-reference-solver:test --file containers/solver.Dockerfile .
bash reference/tests/reference_container_test.sh
```

The Dockerfile pins the official DOLFINx multi-architecture manifest by digest.
It installs Gmsh and its C++ headers, builds the C++20 `mesh-audit` executable,
runs its CTest suite, then runs both public commands while building the image,
including a real plane-strain solve and all-level convergence gate.

## Public command

```sh
docker --context orbstack run --rm -v "$(pwd)/reference/runs:/artifacts" \
  cmc-reference-solver:test converge-case --output /artifacts
```

The V2 fixed-crack bridging tracer uses the same audited geometry but adds one
prescribed, linearly tapered closure-traction load. It is not a calibrated CMC
material model:

```sh
docker --context orbstack run --rm -v "$(pwd)/reference/runs:/artifacts" \
  cmc-reference-solver:test converge-bridged-case --output /artifacts
```

Its `provenance-convergence.json` records mesh/contour agreement and runtime,
but intentionally has no NASA comparison or analytical-authority field. Its
domain integral is a diagnostic for the declared loading, not a path-independent
material toughness.

The command writes:

- `levels/{coarse,medium,fine}/`: the declared mesh sizes, audits, solved fields,
  and per-level J summaries;
- `provenance-convergence.json`: runtime, mesh statistics, two contour values at
  every level, NASA comparison, gates, and adjudication;
- `case-visual.svg`: a deterministic view rendered from the actual generated
  medium mesh and its declared load, support, and crack-face geometry.

The generator uses Gmsh's Crack plugin to turn the declared `crack_trace` into
two topologically separate `crack_faces`; `mesh-audit` rejects a mesh that
lacks that opened topology. Domain-integral J convergence uses the two independently declared radii (8 and 12 mm), compares
the fine result with the fixed NASA correction value, and fails closed to an
`indeterminate` artifact when any declared gate is missed. The result remains a
numerical reference for this bounded isotropic benchmark, not experimental truth.

`mesh-audit` is intentionally hard-coded to the shared edge-cracked-plate
geometry; it checks its physical entities, dimensions, crack trace, quadratic
triangles, and minimum mesh quality. A V2 case with different geometry must
provide an explicit audit-contract input rather than accumulating case-specific
branches.

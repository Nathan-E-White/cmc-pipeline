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
runs its CTest suite, and smoke-tests the V1 and prescribed-traction V2
commands. The dedicated container test runs the full reversible program.

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

The reversible cohesive tracer is a separate public command. It uses a
generator-owned paired-lip artifact and a synthetic, history-free bilinear
normal-opening law under monotonic prescribed top displacement:

```sh
docker --context orbstack run --rm -v "$(pwd)/reference/runs:/artifacts" \
  cmc-reference-solver:test converge-reversible-cohesive-case --output /artifacts
```

It writes `reversible-cohesive-convergence.json`, `case-visual.svg`, and one
directory per declared mesh level. Every program attempt is retained under
`single-step-attempts/`; each level is explicitly `solved`, `failed`, or
`indeterminate`. Refinement comparisons appear only when all three levels are
solved with complete accounting. The command reports reaction, external work,
bulk strain energy, reversible interface potential, and diagnostic-only J.
Those quantities are numerical evidence within this synthetic fixed-crack
model—not fracture energy, toughness, calibration, physical validation,
qualification, or design authority. Compression is rejected rather than
treated as contact or silently repaired.

`acceptance` is separate from the per-level solve statuses. It is available
only when all three levels solve, and then applies the declared 2.5% fine/
medium checks to reaction, interface potential, mouth opening, and both J
diagnostics, plus the fine energy-closure requirement below 1%. A rejected or
unavailable acceptance record is evidence of an incomplete tracer, not a
numerical qualification.

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

# V2 reversible cohesive tracer: implementation plan

## Status and authorization

This is an approved implementation plan, not an implementation result.  It
extends the already-completed prescribed closure-traction tracer at commit
`390afdc`; it must leave that tracer and V1 unchanged as comparators.

The objective is one fixed, straight, opened-crack numerical tracer with a
history-free, reversible, normal-opening law.  It is not a calibrated CMC
model, a fibre/interface-resolved model, an irreversible damage model, or a
crack-growth model.

## Declared model

Use one synthetic parameter card, with no SiC/SiC property claim:

\[
t_p=20\ \mathrm{MPa},\qquad
\delta_f=0.10\ \mathrm{mm},\qquad
\delta_p=0.010\ \mathrm{mm},\qquad
K=t_p/\delta_p=2{,}000\ \mathrm{MPa/mm}.
\]

The normal traction is the continuous bilinear function

\[
t(\delta)=
\begin{cases}
K\delta & 0\le\delta\le\delta_p,\\
t_p(\delta_f-\delta)/(\delta_f-\delta_p) & \delta_p<\delta<\delta_f,\\
0 & \delta\ge\delta_f.
\end{cases}
\]

Its reported interface quantity is a *reversible interface potential*, not
fracture energy, toughness, or a dissipated quantity.  Opening is defined once
by \(\delta=(u^+-u^-)\cdot n\), where the generated artifact records the
normal from the minus lip to the plus lip.  A negative quadrature-point
opening fails the run: contact, compression, friction, irreversible damage,
and crack advance are out of scope.

The bulk remains a synthetic isotropic plane-strain solid using the current
nominal elastic constants.  The run uses monotonic top-boundary displacement
control and stops at the event \(\delta_\mathrm{mouth}=\delta_f\).  If a step
crosses the event, bracket and bisect the final displacement until the mouth
opening is within \(10^{-4}\delta_f\).

## Deep modules and artifact contract

Do not add a generic cohesive/contact framework.  Add these narrow modules:

1. `BilinearModeIOpeningLaw` owns configuration validation and evaluates
   traction, tangent, and reversible potential at a non-negative opening.  It
   rejects invalid parameter ordering and negative input.  It has no mesh,
   PETSc, or case-card knowledge.
2. `OpenedCrackMeshArtifacts` is the generator-owned result: mesh, existing
   mesh audit, and a required standalone `crack-face-pairs.json`.  The solver
   consumes the map and never infers pairing from Gmsh entity order, current
   coordinates, or a physical-group tag.
3. `PairedLipAssembler` owns interpolation on a declared pair, breakpoint
   subdivision, equal-and-opposite residual contribution, and consistent
   tangent contribution.  It must use paired exterior facets, never `dS`,
   mortar, or a contact formulation.
4. `MonotonicDisplacementProgram` owns load-factor steps, Newton/cutback
   policy, endpoint bracketing, and increment evidence.  It must not alter a
   law parameter or solver method after a nonlinear failure.

`crack-face-pairs.json` is a separately validated public artifact.  It must
contain a version, mesh digest, reference-trace ID/direction/units, tolerance,
tip policy, normal/tangent convention, quadrature convention, and ordered
element pairs.  Each pair must include minus/plus element identifiers,
node identifiers, reference-node correspondences, and the reference-coordinate
mapping.  The shared sealed crack-tip endpoint is explicitly excluded from
interface quadrature.  The generator records correspondence while the Gmsh
Crack plugin duplication remains observable, before node renumbering; the map
is updated to exported identifiers rather than reconstructed later.

The parameter card must carry a small provenance record with
`authority: synthetic` and `non_calibrated: true`.  A future measured card may
replace it only with declared architecture, fibre/interphase system,
temperature/environment, specimen geometry, source, inverse-identification
method, and unloading/reloading evidence.  Do not add that future material
module now.

## Numerical procedure and kill switch

At each matched quadratic lip pair, find all reference-coordinate roots of
\(\delta(\xi)=\delta_p\) and \(\delta(\xi)=\delta_f\) inside the pair.
Subdivide at those roots, then use three-point Gauss integration on each smooth
subinterval.  Three points alone are not adequate across a bilinear kink;
within a branch they integrate the quadratic-interpolation residual and
consistent tangent exactly for this straight-trace case.

Solve each attempted displacement increment with at most 25 Newton iterations.
On failure, halve the increment.  Abort and write a failed/indeterminate
artifact after eight consecutive cutbacks or a normalized increment below
\(10^{-4}\).  Newton convergence requires relative residual \(\le10^{-8}\).
Record rejected attempts and their residual histories; do not conceal them.

## Required implementation sequence

1. Add the new case card and schema validation for the synthetic provenance,
   law parameters, displacement program, and declared exclusions.
2. Extend the mesh generator to write and validate coupled opened-crack
   artifacts at every mesh level.  Preserve the existing V1 and prescribed
   traction commands byte-for-byte in behavior.
3. Implement and unit-test the law independently, including both kinks,
   zero traction beyond \(\delta_f\), and rejected compression/configuration.
4. Implement the paired-lip residual and consistent tangent from the artifact
   map, then couple it to a PETSc nonlinear solve under displacement control.
5. Implement the monotonic program, cutback limits, endpoint bisection, and
   per-increment evidence.
6. Extend convergence orchestration and container validation for the new
   public command.  Keep J as a diagnostic only; no NASA analytical-authority
   field or toughness comparison is permitted for this case.
7. Update the README, ADR, case visual, and claim-boundary checks only after
   the executable artifacts support them.

## Verification and acceptance

Required tests, in addition to existing V1 and prescribed-traction V2 tests:

- artifact topology, bijection, orientation, mesh-digest, and sealed-tip
  exclusion checks; malformed or stale maps fail before solve;
- paired-lip patch tests for uniform opening, rigid translation/rotation,
  equal-and-opposite forces, and enumeration invariance;
- zero-traction-law regression to the displacement-controlled elastic
  baseline;
- law-branch and breakpoint-subdivision tests, including crossing one and both
  kinks within an element;
- nonlinear kill-switch tests for iteration cap, cutback exhaustion, and
  negative opening;
- mesh and displacement-increment refinement of reaction, interface
  potential, mouth-opening event, and J diagnostic;
- final energy closure \(W_\mathrm{external}\approx
  U_\mathrm{bulk}+\Pi_\mathrm{interface}\) within 1% after increment
  refinement.

The accepted artifact must list per increment: prescribed displacement/load
factor, mouth opening, reaction, external work, bulk strain energy, reversible
interface potential, Newton iterations/residual, cutbacks, and J diagnostic.
Failure remains an explicit failed or indeterminate result.

## Non-goals and future gates

V3 is the earliest possible scope for irreversibility, debonding, frictional
slip, fibre failure, fatigue, or crack growth.  Contact/compression is V4, if
ever pursued.  Thermal coupling and surrogate work are also out of this slice.

Published evidence does not provide admissible calibrated values for this
specific reversible effective crack-plane law.  The parameter decision and
future calibration admission criteria are supported by
`doc/research-cmc-bridging-parameter-authority.md`; the paired-lip basis is
documented in `doc/research-paired-crack-face-discretization.md` and
`doc/research-paired-crack-lips.md`.

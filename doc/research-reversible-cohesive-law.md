# Design research: reversible bridging traction--separation law

## Decision addressed

For the next V2 fixed-matrix-crack tracer, choose a **single-valued, reversible
Mode-I bridging traction law**.  The model is a screening constitutive response
on already-open crack faces; it is not a calibrated fibre/matrix interface,
damage/debond model, or crack-growth criterion.

## Recommendation

Use a **piecewise-linear (bilinear) conservative law** for the V2 slice:

\[
t(\delta)=
\begin{cases}
 K\delta, & 0\le\delta\le\delta_p,\\
 t_p\dfrac{\delta_f-\delta}{\delta_f-\delta_p},
   & \delta_p<\delta\le\delta_f,\\
 0, & \delta>\delta_f,
\end{cases}
\qquad \delta_p=t_p/K.
\]

Declare the three inputs explicitly: initial stiffness \(K\), peak traction
\(t_p\), and zero-traction separation \(\delta_f\).  Enforce
\(0<\delta_p<\delta_f\).  This makes the peak, initial compliance, range of
bridging, and area under the monotonic curve inspectable.  The latter is
\(\int_0^{\delta_f}t\,d\delta=t_p\delta_f/2\), which is useful as a
*recoverable interface-potential scale*, not as fracture energy.

The choice is a matter of auditable scope, not superior CMC fidelity.  A
piecewise-linear law is commonly used in composite-interface cohesive
formulations: NASA's Camanho--Dávila technical memorandum presents a
bilinear, mixed-mode decohesion element formulation for composite
delamination.  Tvergaard and Hutchinson identify work of separation and peak
traction as the primary traction--separation parameters in their original
fracture-process analysis.  Those sources concern irreversible fracture or
decohesion when coupled to their relevant evolution rules; they do **not**
validate the proposed reversible CMC bridging parameters.

## Why not exponential for this atomic slice?

The Xu--Needleman-style exponential form has a smooth surface-potential basis;
the current ANSYS theory reference attributes its exponential CZM form to Xu
and Needleman and writes traction as the derivative of a surface potential.
Smoothness can make a Newton solve less awkward locally.  It is not enough to
outweigh the costs here:

- Its characteristic separation is less immediately observable in a case
  review than the bilinear law's peak and zero-traction separations.
- Its tail approaches zero asymptotically, so an implementation must invent a
  cut-off for a finite bridging zone and for visual/audit output.
- Changing shape requires changing the analytical form; the bilinear law keeps
  the three requested, separately auditable quantities explicit.

An exponential law remains a reasonable later *sensitivity alternative*, once
the project has a stated data source or micro-mechanistic reason for preferring
its shape.  It should not be introduced merely because a smooth curve is more
flattering in a plot.

## Reversibility and energy/J consequences

The law above must be implemented as a potential-derived, **history-free**
response: at a given opening \(\delta\), loading and unloading return the same
traction.  Consequently a closed opening--traction cycle returns its work;
there is no dissipated cohesive fracture energy, damage variable, debond state,
or residual opening.  Calling the area under the initial opening path
``Gc``, toughness, or a CMC R-curve would be false.

There is a numerical price.  The softening limb has negative tangent stiffness,
so quasi-static equilibrium may lose stability under simple load control even
though the law is reversible.  V2 should therefore specify the loading/control
method, use displacement or continuation control as needed, and report solver
convergence.  The non-smooth corner at \(\delta_p\) is also a known but modest
Newton event; use an explicit branch/tangent test or a documented local
regularisation.  Do not smuggle in viscous regularisation unless it is recorded
as a numerical device, since it makes the response rate-dependent and no
longer exactly reversible.

Rice's original derivation supports path independence for elastic or
deformation-theory elastic-plastic two-dimensional fields.  A conservative,
fixed-interface potential can be included in a total-potential/energy balance,
but a bulk-only V1-style contour integral that crosses or omits bridging work
is not automatically a path-independent crack-driving quantity.  For this
fixed-crack V2 tracer, report the contour result only as a diagnostic and add
an interface-potential and global external-work balance.  Reserve a fracture
energy or propagation interpretation for V3, when an irreversible evolution
law and its verification are approved.

## Minimum V2 implementation and verification contract

1. Mode I only; tension-opening convention, units, and compression/contact
   handling must be declared.  No tangential traction, friction, damage,
   fibre failure, thermal field, calibration, or crack advance.
2. Record \(K,t_p,\delta_p,\delta_f\), the law version, and a fixed finite
   bridging-zone extent in every artifact.
3. Test point values and tangent on both branches; zero traction beyond
   \(\delta_f\); continuity at \(\delta_p\) and \(\delta_f\); and identical
   traction/work for a prescribed opening--closing cycle.
4. Test limiting cases: \(t_p\to0\) recovers the unbridged fixed crack; a
   sufficiently large \(\delta_f\) with a specified regime should approach a
   declared closure-loading comparator, not be claimed equivalent without
   numerical evidence.
5. Audit mesh and nonlinear-solver convergence separately, then report global
   external work, bulk strain energy, and reversible interface potential.  Do
   not use J-contour independence alone as validation of the cohesive response.

## Sources

- J. R. Rice, [*A Path Independent Integral and the Approximate Analysis of
  Strain Concentration by Notches and Cracks* (1968)](https://doi.org/10.1115/1.3601206).
  Original J-integral derivation and its elastic/deformation-theory setting.
- V. Tvergaard and J. W. Hutchinson, [*The Relation Between Crack Growth
  Resistance and Fracture Process Parameters in Elastic-Plastic Solids*
  (1992)](https://groups.seas.harvard.edu/hutchinson/papers/TvergaardHutch1992.pdf).
  Original cohesive-fracture analysis identifying peak traction and work of
  separation as principal process parameters.
- X.-P. Xu and A. Needleman, [*Numerical Simulations of Fast Crack Growth in
  Brittle Solids* (1994)](https://doi.org/10.1016/0022-5096(94)90003-5).
  Original cohesive-surface crack-growth formulation with a characteristic
  separation length.
- P. P. Camanho and C. G. Dávila, [*Mixed-Mode Decohesion Finite Elements for
  the Simulation of Delamination in Composite Materials*, NASA/TM-2002-211737
  (2002)](https://ntrs.nasa.gov/citations/20020078517).  NASA's composite
  interface formulation and piecewise-linear cohesive-law precedent.
- ANSYS, [*Cohesive Zone Material (CZM) Model* (v25.2)](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/ans_thry/thy_mat11.html).
  Authoritative implementation reference for potential-based exponential CZM
  and bilinear alternatives.
- Dassault Systèmes, [*Contact Cohesive Behavior* (Abaqus 2025)](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEITNRefMap/simaitn-c-cohesivebehavior.htm).
  Authoritative distinction between initial elastic traction--separation and
  irreversible damage evolution.

## Limitations

No source above supplies calibrated parameters for this repository's proposed
CMC, proves that a scalar Mode-I law represents fibre bridging, or establishes
that the law predicts matrix-crack resistance.  That requires material-system,
architecture, temperature, and test data, while the deliberately deferred
V3 mechanisms require irreversible state and a new verification argument.

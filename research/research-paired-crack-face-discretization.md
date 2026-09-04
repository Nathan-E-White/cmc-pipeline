# Design research: paired crack-face discretization

## Decision addressed

The V2 fixed-matrix-crack tracer needs a crack-face representation that can
evaluate an opening-dependent, Mode-I bridging traction from the *relative*
displacement of the two sides of the already-open crack.  The present V1/V2
mesh generator uses Gmsh's `Crack` plugin and tags both opened lips as one
`crack_faces` physical group, but the solver currently applies a prescribed
load to that group.  It does not retain or consume a face-pair map.  A
physical group is therefore useful boundary selection metadata, not a
discretization contract for an interface law.

## Recommendation

For this two-dimensional, fixed, straight crack, make **paired crack faces** a
first-class mesh artifact.  Generate both lips from one reference trace and
export a deterministic ordered table of pairs

\[
  (e_i^-, e_i^+,\; \xi\in[-1,1],\; n_i,\; w_i,\; x_i^0),
\]

where `-` and `+` are declared sides, \(x_i^0\) is their common reference
location, \(n_i\) is the declared unit normal from `-` to `+`, and the two
line elements use the same reference coordinate and quadrature rule.  At an
interface quadrature point define the normal opening

\[
  \delta_n(\xi) = [u^+(\xi)-u^-(\xi)]\mathbin{\cdot}n_i .
\]

Then the virtual work of a scalar traction--separation response is evaluated
once per pair, e.g. \(\sum_i\int t(\delta_n)\,\delta v_n\,d\Gamma\), with
equal-and-opposite residual contributions on the two faces.  This is the
smallest auditable construction for the proposed effective crack-plane law;
it deliberately does **not** introduce contact, tangential slip, damage,
debonding, fibre geometry, or crack advance.

Conforming zero-thickness cohesive elements use precisely this conceptual
arrangement: opposing segments/facets, an interpolated displacement gap at
integration points, and virtual-work residual/tangent contributions.  Paggi
and Wriggers describe this standard matching-node construction and distinguish
their node-to-segment/surface alternative for nonmatching faces. [*Node-to-
segment and node-to-surface interface finite elements for fracture mechanics*
(2016)](https://doi.org/10.1016/j.cma.2015.11.023).  [Abaqus's
cohesive-element reference](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEELMRefMap/simaelm-c-cohesiveinit.htm)
also documents corresponding top/bottom nodes, their initially coincident
placement where applicable, and the need to verify orientation.  These are
discretization precedents, not a claim that this repository has implemented
Abaqus elements or a calibrated cohesive material.

## Why a pair map, rather than only `crack_faces`

Gmsh's `Crack` plugin opens a crack by duplicating nodes; for a 1-D crack it
also accepts a reference normal and can place the opened boundary into a new
physical group.  Its manual further exposes an orientation-swap option for the
duplicated elements.  [Gmsh reference manual, `Plugin(Crack)`](https://gmsh.info/doc/texinfo/gmsh.html#Plugin_0028Crack_0029).
Those capabilities create separated topology, but they do not specify which
element on one lip corresponds to which element on the other, nor which
orientation the downstream integrator will use.  In the current generator,
`NormalZ=1` describes the embedding plane of the 1-D trace; it is not a
stored in-plane normal-opening convention.  The implementation must therefore
record the latter independently.  The current `.geo` declares only the crack
mouth as `OpenBoundaryPhysicalGroup`; by the plugin's documented sealing rule,
the crack-tip endpoint remains shared.  The pair contract must therefore
exclude that shared tip from pairwise quadrature (or change the mesh policy),
rather than asserting that every reference-trace node has a distinct mate.

A one-to-one matching partition makes the interface integral local,
deterministic, and easy to test.  Nonmatching opposite-face meshes are
possible, but they need a projection/mortar or node-to-segment formulation;
that additional method must define its master/slave or mortar space,
intersection/projection tolerance, and integration ownership.  The original
[mortar-contact formulation of Belgacem, Hild, Laborde, and Renard
(1998)](https://doi.org/10.1016/S0895-7177(98)00121-6) explicitly addresses
nonmatching grids.  It is a later extension, not a safe implicit fallback for
this tracer.

## Proposed artifact contract

Store the contract separately from the Gmsh physical group and retain it with
each case artifact.  The minimum fields are:

- `reference_trace_id`, reference-coordinate direction, length, units, and
  crack-tip/end-point ownership;
- `minus_face` and `plus_face` element/node identifiers, their interpolation
  order, and the explicit pair ordering;
- `reference_node_pairs` (same \(x^0\) within a declared absolute tolerance),
  plus a per-element map from the shared \(\xi\) to each local element
  coordinate;
- `normal_minus_to_plus` and a right-handed tangent convention; and
- quadrature rule, weights, reference/current measure choice, and the law
  version and parameters that consume the pairs.

Do not derive pairing by sorting current coordinates.  Under deformation this
can swap correspondences, and near a crack tip it makes a constitutive result
depend on an arbitrary tie-break.  Do not infer `+`/`-` from Gmsh element tags:
tags are identifiers, not a physical orientation convention.  Instead, derive
both sides from the pre-open trace and persist the association while the Crack
plugin's duplication is still observable.

For the present straight trace, the normal can be fixed from its declared
reference tangent.  For a curved trace, carry a smoothly oriented local frame
and state how its sign is propagated through the crack front.  This is
necessary because cohesive/interface response distinguishes normal and
tangential directions; the implementation documentation for cohesive elements
likewise requires an explicit stack direction and provides orientation checks.
[Abaqus cohesive-element initial geometry](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEELMRefMap/simaelm-c-cohesiveinit.htm).

## Acceptance tests before a constitutive law is connected

1. **Topology:** two distinct face traces exist over the declared open
   interior; both reproduce the reference length and endpoints to the
   declared tolerance, and their non-tip node IDs are disjoint.  The declared
   tip policy must account for its intentionally shared/sealed node.  This
   demonstrates an opened mesh, not merely a named internal line.
2. **Bijection and orientation:** every required face element/node occurs once
   in the pair map; \(x^-_0=x^+_0\) within tolerance; \(n\) is unit length;
   and reversing the global pair ordering does not reverse the declared
   `minus_to_plus` convention.
3. **Patch tests:** prescribe (a) equal displacement on both faces, yielding
   zero opening and zero internal interface work; (b) uniform normal opening,
   yielding the analytic traction/resultant for the declared law; and (c)
   rigid translation/rotation, yielding no spurious normal opening in the
   stated small-strain reference-frame formulation.
4. **Assembly invariants:** pairwise forces are equal and opposite; interface
   energy/work agrees with the quadrature result; and changing only the face
   element enumeration leaves the result unchanged.
5. **Convergence:** refine both faces together and report opening, resultant,
   interface energy, and the existing bulk/domain-integral diagnostic.  A
   cohesive response is evaluated at element material points, while a
   surface-contact response is evaluated at contact constraints; mesh-density
   effects therefore need their own evidence rather than being folded into
   bulk J-contour agreement. [Abaqus comparison of cohesive elements and
   cohesive contact](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEITNRefMap/simaitn-c-cohesivebehavior.htm).

## Boundary of this recommendation

This is an effective crack-plane numerical construction for a fixed crack.
It does not establish a fibre--matrix interface, fibre bridging distribution,
debonding, frictional slip, fracture energy, R-curve, crack growth, or a
path-independent J quantity after nonconservative mechanisms are added.  The
existing prescribed closure traction should remain a separate V2 comparator:
it has no dependence on paired displacement and therefore does not exercise
this contract.

## Direct sources

- C. Geuzaine and J.-F. Remacle, [*Gmsh: A 3-D finite element mesh generator
  with built-in pre- and post-processing facilities* (2009)](https://doi.org/10.1016/j.finmec.2009.01.002),
  and the [Gmsh reference manual, `Plugin(Crack)`](https://gmsh.info/doc/texinfo/gmsh.html#Plugin_0028Crack_0029).
  The manual is the authoritative source for the plugin's crack-node
  duplication, physical-group, normal, and orientation options.
- Dassault Systèmes, [*Defining the Cohesive Element's Initial Geometry*
  (Abaqus 2025)](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEELMRefMap/simaelm-c-cohesiveinit.htm).
  Authoritative cohesive-element connectivity, coincident-face, and local
  orientation reference.
- Dassault Systèmes, [*Contact Cohesive Behavior* (Abaqus
  2025)](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEITNRefMap/simaitn-c-cohesivebehavior.htm).
  Authoritative distinction between cohesive-element integration and
  surface-contact constraints, including mesh-resolution implications.
- F. B. M. Belgacem, P. Hild, P. Laborde, and P. Renard, [*The mortar finite
  element method for contact problems* (1998)](https://doi.org/10.1016/S0895-7177(98)00121-6).
  Primary nonmatching-interface formulation used here only to delimit the
  deferred alternative.
- M. Paggi and P. Wriggers, [*Node-to-segment and node-to-surface interface
  finite elements for fracture mechanics* (2016)](https://doi.org/10.1016/j.cma.2015.11.023).
  Primary fracture-interface treatment contrasting conforming opposing-face
  elements with a projection-based nonmatching alternative.

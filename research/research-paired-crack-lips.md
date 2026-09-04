# Design research: paired quadratic crack lips for reversible cohesion

## Decision addressed

Can the V2 fixed-crack tracer implement its reversible, Mode-I,
potential-derived traction--separation law by pairing the opposing quadratic
line elements made by the repository's Gmsh \`Crack\` plugin invocation, instead
of introducing mortar or contact machinery?

## Finding

Yes, for this one, fixed, straight edge crack, **provided the matching
quadratic lip discretisation and a face-pair map become explicit audited
invariants**. This is a conforming, matching-interface cohesive construction:
at each common reference-coordinate quadrature point, evaluate the normal
opening, the history-free law, and equal-and-opposite closure forces on the
two lips. It is not a \`dS\`/interior-facet formulation and it is not a mortar
or contact formulation.

The Gmsh Crack plugin is the right mesh operation for the starting topology.
The official manual says that it duplicates the nodes and elements on an
orientable-manifold physical group, with elements on the positive side using
the generated nodes; \`OpenBoundaryPhysicalGroup\` leaves the resulting crack
open, and \`SwapOrientation\` changes the duplicated-element orientation.
[Gmsh Crack plugin](https://gmsh.info/doc/texinfo/gmsh.html#Plugin-Crack)

But neither that contract nor this repository's current \`crack_faces\`
physical group supplies a semantic *upper-to-lower* pairing map. This is
especially material here: the generator calls \`renumberNodes()\` after the
plugin, so node identifiers cannot serve as a durable correspondence. The V2
generator/audit must construct and emit the map from reference geometry; it
must not infer it later from identifiers or from physical-group iteration
order.

## Required V2 contract

For every accepted mesh, \`pair_opened_edge_crack(mesh)\` should produce a
canonical list of pairs:

\`\`\`text
(upper quadratic exterior facet, lower quadratic exterior facet,
 reference arclength interval, orientation, reference normal)
\`\`\`

For this horizontal case, classify by the adjacent cell/reference-side
geometry, match by the crack's undeformed arclength from mouth to tip, and
choose one fixed normal from lower to upper. The module rejects, rather than
guesses through, any of the following:

1. not exactly two disjoint lip traces;
2. unequal lip-element counts, element orders, or reference-arclength
   partitions;
3. no one-to-one quadratic node correspondence under a declared coordinate
   tolerance;
4. inconsistent lip orientation, duplicated pairing, unpaired facets, or an
   unexpected trace/normal; and
5. a trace that differs from the declared 0--30 mm straight reference crack.

The artifact should record the pair count, pair-map digest, tolerance,
quadrature rule/order, chosen normal convention, and the checked matching
result. This makes the relationship independently reviewable after the mesh's
node numbers are normalised.

## Assembly consequence

The opened lips are exterior facets of two separate cell traces, not the two
sides of one shared interior facet. DOLFINx's interior-facet integration
domain is explicitly represented as \`(cell0, local_facet0, cell1,
local_facet1)\` and uses the \`+\`/\`-\` restriction. That structure is not
available once a crack operation has duplicated the nodes. Use an explicit
paired-facet assembly (or a facet submesh with entity maps), not \`jump(u)\` on
\`dS\`. DOLFINx documents both custom exterior-facet integration domains and
facet-submesh entity maps in its HDG demo.
[DOLFINx forms source](https://docs.fenicsproject.org/dolfinx/v0.10.0.post0/python/_modules/dolfinx/fem/forms.html),
[DOLFINx HDG demo](https://docs.fenicsproject.org/dolfinx/v0.10.0.post0/python/demos/demo_hdg.html)

At paired quadrature coordinate \(s\), with the declared lower-to-upper
reference normal \(n\), define

\[
\delta(s)=(u_{upper}(s)-u_{lower}(s))\mathbin{\cdot}n.
\]

V2 admits \(\delta\geq0\) only. It evaluates the already-approved
single-valued law \(t(\delta)\) and its potential \(\psi(\delta)\), then
assembles consistent, equal-and-opposite *closure* forces and the consistent
Newton tangent from \(d t/d\delta\). The integration must use the same
reference coordinate, line Jacobian, weights, and physical measure for both
lips; a sufficient declared quadrature order must be used for the P2 traces
and branch changes. A conservative law gives the interface contribution
\(\int_\Gamma \psi(\delta)\,d\Gamma\); V2 must verify it as part of the global
energy balance, not call it dissipated fracture energy.

The cohesive-force premise is longstanding: distributed crack-face cohesive
forces can act to close a crack, but it does not select or calibrate V2's
reversible bilinear law.
[NASA cohesive-zone synthesis](https://ntrs.nasa.gov/api/citations/19960009413/downloads/19960009413.pdf),
[Barenblatt (1962)](https://doi.org/10.1016/S0065-2156(08)70121-2)

## Why mortar/contact is not in this slice

Mortar methods earn their cost for nonmatching interface meshes; contact earns
its cost for unilateral nonpenetration and possibly friction. V2 deliberately
has matching, fixed, tensile-only lips and rejects negative opening. Neither
extra mechanism improves the fidelity of the stated model, while each adds a
new constraint, multiplier/active-set, or projection contract to verify.

This conclusion does **not** generalise to a later curved, remeshed,
nonmatching, propagating, or closing crack. Any of those changes invalidates
the present pairing assumption and requires a new interface-integration
decision.

## Minimum verification

1. Generate medium and refined meshes and prove every lip pair passes the
   pairing audit; include deliberate asymmetric and missing-pair rejection
   fixtures.
2. On a two-element paired-interface patch, verify force balance, tangent by
   finite difference, potential derivative, and zero net interface force.
3. Prove equivalence under reversed Gmsh element ordering after canonical
   arclength ordering.
4. Exercise the law's zero-traction, elastic, peak, softening, and unloading
   branches; reject negative opening rather than silently imposing contact.
5. Report external work, bulk strain energy, and interface potential under
   load/refinement. The existing bulk-only contour \(J\) remains diagnostic,
   not an automatically path-independent cohesive crack-driving value.

## Scope boundary

This design creates an **effective crack-plane cohesive interface**. It does
not resolve fibres, coatings, or fibre--matrix interfaces; identify calibrated
CMC bridging; represent debonding, friction, fibre failure, crack advance, or
contact; or establish a material toughness.


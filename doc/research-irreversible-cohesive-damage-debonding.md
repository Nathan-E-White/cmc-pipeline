# Research note: irreversible cohesive damage and debonding

## Scope

This note sharpens terminology for a future CMC-inspired fracture model. It
does not change the implemented V2 fixed-crack prescribed-bridging tracer. That
tracer has no opening-dependent interface state, damage evolution, debonding,
or friction.

## Findings and terminology boundary

Irreversible cohesive damage and fibre--matrix debonding are related but
different concepts.

- **Irreversible cohesive damage** is a constitutive representation, not a
  microstructural observation.  It is a traction--separation relation with
  internal state: the relation must say when damage initiates, how it grows,
  what unloading/reloading does, and when an interface becomes a free surface.
  This is the role played by the displacement-based damage parameter in
  NASA's mixed-mode decohesion element, and by the irreversible cohesive laws
  of Ortiz and Pandolfi. [Camanho, Dávila and de Moura
  (2001)](https://ntrs.nasa.gov/citations/20010044119), [Ortiz and Pandolfi
  (1999)](https://doi.org/10.1002/(SICI)1097-0207(19990330)44:9%3C1267::AID-NME486%3E3.0.CO;2-7)
- **Debond initiation** is the physical onset of adhesion loss at a
  fibre--matrix interface. **Debond propagation** is growth of that failed
  region. Modelling either makes a physical interface claim that is stronger
  than merely applying a closure load across an already opened matrix crack.
- **Frictional slip**, **fibre fracture**, and **pullout** are separate
  mechanisms. They may follow debonding, but a model must not infer them from a
  cohesive damage variable alone.

Budiansky, Hutchinson, and Evans explicitly distinguish initially unbonded
interfaces that can slide frictionally from weakly bonded interfaces that can
debond near a matrix crack. Their result makes the useful point that an
interface regime is part of the model assumption, not decorative terminology.
[Budiansky, Hutchinson, and Evans (1986)](https://doi.org/10.1016/0022-5096(86)90035-9)

NASA's CMC toughening overview separately identifies matrix cracking, interface debonding, relative
sliding, intact-fibre bridging, fibre fracture and pullout. A cohesive law
therefore represents only the portion of that sequence covered by its declared
state and contact laws. [NASA, *Toughening Mechanisms in Ceramic Matrix
Composites*](https://ntrs.nasa.gov/citations/19880013027)

## A minimal law is a modelling choice, not a material claim

For a scalar normal-opening tracer, one deliberately limited choice is

\[
\kappa(t) = \max_{\tau \leq t} \delta_{\mathrm{eff}}(\tau),
\qquad \dot d \geq 0,
\]

where \(\delta_{\mathrm{eff}}\) is a *declared* effective separation,
\(\kappa\) is a maximum-opening history and \(d \in [0,1]\) is damage. This
is an admissible scalar construction; it does not follow uniquely from the
papers and it does not identify a CMC interface. The implementation must give
the tensile traction on loading, unloading, reloading and at \(d=1\), and
must prohibit healing unless healing is explicitly a different constitutive
model.  The irreversible-law precedent is that separation is governed by the
cohesive law until free surfaces form; a solver cannot obtain that state merely
from a softening-looking loading curve. [Ortiz and Pandolfi
(1999)](https://doi.org/10.1002/(SICI)1097-0207(19990330)44:9%3C1267::AID-NME486%3E3.0.CO;2-7)

For monotonic opening, a bilinear envelope may expose an initiation separation
and a complete-failure separation. In mixed mode, however, a scalar effective
separation additionally chooses a mode-interaction criterion and a partition
of normal and tangential work. NASA's formulation explicitly addresses
mixed-mode initiation and propagation; a Mode-I-only tracer should instead
exclude shear, rather than inherit the word “mixed mode.” [Camanho and Dávila,
*Mixed-Mode Decohesion Finite Elements* (2002)](https://ntrs.nasa.gov/citations/20020053651)

Energy needs equally explicit bookkeeping. A cohesive formulation may store
recoverable energy before unloading and dissipate energy as damage advances;
their difference is path dependent once irreversible state evolves.  Thus the
area below a first-loading traction--separation curve is not, by itself,
evidence that the present tracer has identified a material fracture energy.
The original cohesive-fracture analysis treats peak traction and work of
separation as process parameters, while the original \(J\)-integral result is
an elastic/deformation-theory construction; neither supplies path independence
for an arbitrary evolving, bulk-only contour calculation. [Tvergaard and
Hutchinson (1992)](https://groups.seas.harvard.edu/hutchinson/papers/TvergaardHutch1992.pdf),
[Rice (1968)](https://doi.org/10.1115/1.3601206)

The 1990 fibre--matrix analysis by Sutcu and Hillig relates a
debond work to a characteristic debond shear stress and to a separate
frictional sliding resistance. That supports keeping adhesion/debond and
post-debond friction as separate parameters, rather than calling every
softening parameter “interface strength.” [Sutcu and Hillig
(1990)](https://doi.org/10.1016/0956-7151(90)90278-O)

## What would be established, and what would remain a choice

| Statement | Status in a later slice |
| --- | --- |
| An irreversible cohesive element can evolve from cohesion to free surfaces. | Established mechanics/implementation precedent, not evidence for this material system. |
| A fibre--matrix interface can be initially weakly bonded, then debond and slide frictionally. | Established CMC micromechanical regime; still needs this system's architecture and parameters. |
| The project uses a scalar Mode-I bilinear law on a fixed effective crack plane. | Deliberate model choice. It is not a resolved fibre--matrix interface model. |
| The chosen parameters predict CMC matrix-crack resistance, pullout, or life. | Unsupported until calibrated and independently validated. |

## Implications for a later implementation

An irreversible cohesive/debonding slice requires all of the following before
it can claim more than a numerical constitutive experiment:

1. A declared interface: resolved fibre--matrix interface or explicitly named
   effective crack-plane interface.
2. A face-pairing or interface-element representation that measures relative
   opening between the two sides. The current mesh exposes crack faces but not
   a public face-pairing contract.
3. A loading-history state and a non-healing rule, plus restart/provenance
   treatment for that state.
4. Separate treatment or explicit exclusion of compression/contact and shear;
   otherwise “debonding” can conceal unmodelled interpenetration or friction.
5. Verification beyond the current contour-agreement gate: limiting elastic
   response, monotone damage, unloading/reloading, energy balance, and complete
   failure. Compare external work, bulk strain energy, recoverable cohesive
   energy and cumulative dissipation. A standard elastic-domain \(J\) value is
   not automatically path-independent once damage evolves.

## Verification cases that make the boundary testable

1. **No-damage limit.** Keep \(\kappa\) below initiation under opening and
   closure. The model must reduce to its declared elastic cohesive response
   with zero damage dissipation.
2. **One excursion, then unload.** Cross initiation, unload and reload below
   the prior maximum. Damage must not decrease and the specified unload/reload
   trajectory must be reproduced. This distinguishes irreversibility from the
   current reversible bridging law.
3. **Complete failure.** Reach the stated terminal separation. Tensile
   cohesive traction must be zero thereafter; compression and contact must be
   either separately exercised or explicitly out of scope.
4. **Mode exclusion.** Apply a tangential displacement or compression in a
   diagnostic test. A Mode-I-only implementation must reject it or report it
   as excluded; silently accepting it would make an undeclared mixed-mode or
   contact claim.
5. **Energy and restart.** Record history state, work partitions and the law
   version. A restart must reproduce the same state and subsequent response;
   otherwise “non-healing” is not an auditable property.
6. **Mesh/objectivity.** Repeat the complete-separation case with a refined
   interface discretisation and compare the declared dissipated energy. Cohesive
   strength, fracture energy, cohesive-zone length and element size interact;
   the parameter set is not credible simply because a single mesh converged.
   [Turon *et al.* (2007)](https://doi.org/10.1016/j.engfracmech.2006.08.025)

## Recommendation

Keep irreversible cohesive damage and fibre--matrix debonding deferred from
the current V2 tracer. If introduced later, begin with a fixed crack and a
single normal-opening, bilinear cohesive law with an explicit nondecreasing
history variable. Call it **irreversible cohesive damage on an effective crack
plane** unless the geometry, parameters, and verification actually establish a
fibre--matrix interface debonding model. Frictional slip, fibre fracture,
pullout, thermal effects, and crack growth should remain separate subsequent
decisions.

## Sources

- B. Budiansky, J. W. Hutchinson and A. G. Evans, [*Matrix Fracture in
  Fiber-Reinforced Ceramics* (1986)](https://web-static-aws.seas.harvard.edu/hutchinson/papers/382.pdf), *Journal of the Mechanics and Physics of Solids* 34, 167--189, [DOI](https://doi.org/10.1016/0022-5096(86)90035-9). Original CMC micromechanics distinguishing weak bonding/debonding from initially unbonded frictional slip.
- M. Sutcu and W. B. Hillig, [*The Effect of Fiber-Matrix
  Debond Energy on the Matrix Cracking Strength and the Debond Shear Strength*
  (1990)](https://doi.org/10.1016/0956-7151(90)90278-O), *Acta Metallurgica et Materialia* 38, 2653--2662. Original energy-balance treatment separating debond work and sliding resistance.
- M. Ortiz and A. Pandolfi, [*Finite-Deformation Irreversible Cohesive
  Elements for Three-Dimensional Crack-Propagation Analysis* (1999)](https://doi.org/10.1002/(SICI)1097-0207(19990330)44:9%3C1267::AID-NME486%3E3.0.CO;2-7), *International Journal for Numerical Methods in Engineering* 44, 1267--1282. Original irreversible cohesive-element formulation.
- P. P. Camanho and C. G. Dávila, [*Mixed-Mode Decohesion Finite Elements for
  the Simulation of Delamination in Composite Materials*, NASA/TM-2002-211737
  (2002)](https://ntrs.nasa.gov/citations/20020053651). NASA primary technical memorandum for initiation, evolution and mixed-mode interface formulation.
- C. G. Dávila, P. P. Camanho and M. F. de Moura, [*Mixed-Mode Decohesion
  Elements for Analyses of Progressive Delamination* (2001)](https://ntrs.nasa.gov/citations/20010044119). NASA/AIAA primary formulation using a displacement-based interface damage parameter.
- V. Tvergaard and J. W. Hutchinson, [*The Relation Between Crack Growth
  Resistance and Fracture Process Parameters in Elastic-Plastic Solids*
  (1992)](https://groups.seas.harvard.edu/hutchinson/papers/TvergaardHutch1992.pdf), *Journal of the Mechanics and Physics of Solids* 40, 1377--1397. Original cohesive-fracture process-parameter analysis.
- J. R. Rice, [*A Path Independent Integral and the Approximate Analysis of
  Strain Concentration by Notches and Cracks* (1968)](https://doi.org/10.1115/1.3601206), *Journal of Applied Mechanics* 35, 379--386. Original \(J\)-integral derivation.
- J. M. Turon, C. G. Dávila, P. P. Camanho and J. Costa, [*An Engineering
  Solution for Mesh Size Effects in the Simulation of Delamination Using
  Cohesive Zone Models* (2007)](https://doi.org/10.1016/j.engfracmech.2006.08.025), *Engineering Fracture Mechanics* 74, 1665--1682. Original mesh-size/energy-dissipation analysis for cohesive-zone simulations.

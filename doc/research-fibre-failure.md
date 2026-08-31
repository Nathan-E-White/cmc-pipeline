# Research note: fibre fracture in ceramic-matrix composites

## Scope

This note identifies the physical distinction and minimum modelling commitments
for **fibre fracture** in a future CMC fracture model. It does not alter the
implemented V2 fixed-crack prescribed-bridging tracer. That tracer has neither
individual fibres nor a fibre-strength distribution, load redistribution,
interface slip, fibre-break state, or crack advance; its closure traction must
therefore not be described as fibre fracture or a fibre-fracture law.

## Finding

In a continuous-fibre brittle-matrix composite, matrix cracking, interface
debonds, sliding, intact-fibre bridging, fibre fracture, and pullout are
distinct mechanisms. Their order and extent depend on the declared constituent
and interface properties. Marshall and Evans identify these mechanisms as the
basis for non-catastrophic response in ceramic-fibre/ceramic-matrix composites;
they are not interchangeable labels for a single softening curve.
[Marshall and Evans (1985), original paper](https://doi.org/10.1111/j.1151-2916.1985.tb15313.x)

A matrix crack can concentrate axial stress in the bridging fibres. Whether a
fibre then fractures depends on a fibre-strength population and on the stress
transfer permitted by the interface. Budiansky, Hutchinson, and Evans analyse
matrix fracture with both initially unbonded frictional interfaces and weakly
bonded interfaces that debond near a matrix crack; this makes the interface
regime an explicit physical assumption, not a consequence that a generic
damage variable can supply.
[Budiansky, Hutchinson, and Evans (1986), original paper](https://doi.org/10.1016/0022-5096(86)90035-9)

Curtin's tensile model makes the resulting modelling dependency concrete: it
uses statistically distributed fibre strengths, a sliding resistance, and a
global-load-sharing assumption after fibre fracture to predict fragmentation,
pullout work, and ultimate tensile strength. The model is valuable as a
bounded homogenised candidate, but global load sharing is an assumption to
declare and test, not a general result for a resolved woven or spatially local
CMC architecture.
[Curtin (1991), original paper](https://doi.org/10.1111/j.1151-2916.1991.tb06852.x)

Fibre fracture and matrix-crack extension are competing initiation mechanisms,
not two names for a composite failure threshold. Marshall and Cox derive
strength--crack-size transitions for failure initiated by either matrix-crack
growth or fracture of bridging fibres. A future event-driven model must
therefore declare separate criteria and the rule by which it selects or couples
them.
[Marshall and Cox (1987), original paper](https://doi.org/10.1016/0001-6160(87)90260-4)

NASA's experimental CMC documentation reports the observed tensile sequence of
matrix cracking, fibre--matrix debonding, fibre pullout, and fibre breakage,
and separately notes that in-situ radiography can observe damage accumulation.
This supports treating constituent-level failure-state predictions as claims
requiring constituent-sensitive evidence rather than inferring them from the
current continuum traction field.
[NASA report on X-ray monitoring of CMC damage and failure](https://ntrs.nasa.gov/api/citations/19940019601/downloads/19940019601.pdf)

## Terms to keep separate

- **Fibre fracture**: loss of load-carrying continuity of a fibre segment under
  a declared fibre-failure criterion and local stress history. It is not
  interface debonding,
  slip, pullout, or matrix cracking.
- **Fibre fragmentation**: accumulation of multiple fibre breaks that creates
  shorter load-bearing segments. It is a population-level outcome, not a
  synonym for the first fibre break.
- **Fibre-strength distribution**: the declared statistical model for failure
  strengths, including its reference length or gauge convention. A deterministic
  threshold has no such size effect and is a different model.
- **Load redistribution rule**: the declared transfer of load after a fibre
  break, for example Curtin's global-load-sharing approximation. A rule is
  required because a break changes the stresses that drive further failures.
- **Pullout**: post-break extraction or sliding of a fibre segment from the
  matrix after the relevant interface has debonded. It must not be assumed just
  because a fibre has broken.

## Candidate model levels

| Level | State and inputs required | Claim boundary |
| --- | --- | --- |
| Prescribed closure traction (current V2) | A spatial traction profile only | A fixed numerical bridging tracer; no fibres, breakage, or interface physics. |
| Homogenised stochastic fragmentation | Fibre volume fraction/radius, modulus, strength-distribution parameters with reference length, interface sliding resistance, and an explicit redistribution assumption | A stated micromechanical approximation for the declared architecture and loading; not resolved fibre positions or local failure paths. |
| Resolved fibre/interface model | Fibre geometry, fibre and matrix constitutive laws, interface debond/slip/contact laws, fibre-break criterion, and a redistribution result arising from equilibrium | A numerical constituent model, which still needs calibration and independent physical adjudication before material or design claims. |

## Minimum contract for a later fibre-fracture slice

Before a model reports fibre breakage, fragmentation, pullout work, or a
strength change caused by fibre fracture, it needs all of the following:

1. A declared model level and architecture: aligned homogenised bundle versus
   resolved individual fibres. A 2-D fixed-crack continuum field alone cannot
   identify a physical fibre that has broken.
2. A fibre-failure criterion: deterministic strength or a named distribution,
   including units, reference gauge length, sampling/reproducibility policy,
   and how thermal or environmental degradation is included or excluded.
3. A post-break equilibrium rule. For a homogenised model, state whether load
   sharing is global, local, or otherwise derived; for a resolved model, prove
   it through the actual equilibrium solution.
4. A separately declared interface regime: bonded, debonding, sliding, and
   compression/contact behaviour. Fibre breakage cannot establish any of these
   states by itself.
5. Verification cases that exercise no-break elastic response, one-break load
   redistribution, monotonic break-state evolution, limiting interface cases,
   and deterministic seeded statistical replay. Compare with experimental
   evidence before calling a predicted failure population physically
   adjudicated.

## Recommendation

Keep fibre fracture outside V2. The smallest later extension that can honestly
use the term is a **homogenised stochastic fibre-fragmentation tracer** with a
declared strength distribution, reference length, interface sliding resistance,
and explicit global-load-sharing assumption. It should remain distinct from
the existing prescribed bridging traction and from irreversible cohesive
damage/debonding. Resolved fibre breaks, local redistribution, pullout, crack
growth, thermal degradation, and calibration are separate subsequent scope.

## Primary sources

- Marshall, D. B., and Evans, A. G. (1985). *Failure Mechanisms in
  Ceramic-Fiber/Ceramic-Matrix Composites*. *Journal of the American Ceramic
  Society*, 68(5), 225--231.
  [DOI](https://doi.org/10.1111/j.1151-2916.1985.tb15313.x)
- Budiansky, B., Hutchinson, J. W., and Evans, A. G. (1986). *Matrix Fracture
  in Fiber-Reinforced Ceramics*. *Journal of the Mechanics and Physics of
  Solids*, 34(2), 167--189.
  [DOI](https://doi.org/10.1016/0022-5096(86)90035-9)
- Curtin, W. A. (1991). *Theory of Mechanical Properties of Ceramic-Matrix
  Composites*. *Journal of the American Ceramic Society*, 74(11), 2837--2845.
  [DOI](https://doi.org/10.1111/j.1151-2916.1991.tb06852.x)
- Marshall, D. B., and Cox, B. N. (1987). *Tensile Fracture of Brittle Matrix
  Composites: Influence of Fiber Strength*. *Acta Metallurgica*, 35(11),
  2607--2619. [DOI](https://doi.org/10.1016/0001-6160(87)90260-4)
- Gyekenyesi, A. L. (1993). *X-ray Monitoring of Damage and Failure in
  Ceramic Matrix Composites*. NASA technical report.
  [NTRS record and report](https://ntrs.nasa.gov/citations/19940019601)

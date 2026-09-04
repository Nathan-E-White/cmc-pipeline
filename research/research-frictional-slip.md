# Research note: frictional slip in fibre-reinforced ceramic-matrix composites

## Scope and terminology

This note concerns **frictional interfacial sliding**: relative motion of a
fibre and its surrounding matrix or interphase along an interface that is
already unbonded over the sliding length. It does not make the present
fixed-crack tracer a resolved-interface model.

Three terms must remain separate:

- **Interfacial debonding** creates or advances the fibre--matrix (or
  fibre--interphase) interface crack.
- **Frictional interfacial sliding** dissipates work as the two surfaces move
  along that debond.
- **Fibre pullout** is the later extraction process, normally after fibre
  fracture, and includes work against the remaining sliding resistance.

This distinction is physical, not merely linguistic. Budiansky, Hutchinson,
and Evans distinguish initially unbonded, frictionally slipping fibres from
initially weakly bonded fibres that debond at a matrix-crack tip; NASA's CMC
overview likewise depicts debonding and relative sliding before fibre fracture
and pullout. [Budiansky, Hutchinson, and Evans (1986)](https://doi.org/10.1016/0022-5096(86)90035-9)
[NASA, *Continuous Fiber Ceramic Matrix Composites for Heat Engine Components*
(1988)](https://ntrs.nasa.gov/citations/19880013027)

## Mechanism and role in composite fracture

Under longitudinal loading, a matrix crack can reach intact reinforcing fibres.
If the interface is sufficiently compliant or weak, local stresses can advance
an interface debond. Subsequent crack opening drives axial relative motion of
the fibre against the matrix/interphase; the interface transfers shear and
turns part of the external work into frictional dissipation. While intact,
fibres bridge the matrix crack and supply closure traction. If they eventually
fracture, the broken embedded lengths can pull out, doing additional frictional
work. This staged description is supported by the original in-situ CMC failure
observations and NASA's mechanism summary; it is not a guarantee that every
CMC, architecture, temperature, or loading history follows the same order.
[Marshall and Evans (1985)](https://doi.org/10.1111/j.1151-2916.1985.tb15313.x)
[NASA (1988)](https://ntrs.nasa.gov/citations/19880013027)

Slip is therefore neither a cohesive opening law nor a substitute for fibre
failure. It affects the bridging force and matrix-cracking resistance through
shear transfer and dissipation, whereas debonding requires an interface-crack
initiation/propagation criterion and fibre fracture requires a fibre-strength
or fibre-damage criterion. The pullout work is not available until the model
also represents the fractured fibre and its embedded length.

## Parameters that need explicit meaning

At minimum, a resolved frictional-slip model needs the following independently
declared quantities:

| Quantity | Meaning and modelling caution |
| --- | --- |
| \(\Gamma_d\) | Work of interfacial debonding (or an equivalent fracture-energy law); it controls creation/extension of the debond, not post-debond sliding by itself. |
| \(\tau_d\) | Critical shear traction used in a particular debond-initiation model. It is not automatically the frictional shear resistance. |
| \(\tau_f\), \(\mu\), or a slip law | Post-debond sliding resistance, represented in different models as a constant shear stress, Coulomb friction, or a displacement/state-dependent law. The normal contact pressure convention must be stated when using \(\mu\). |
| \(\sigma_0\) / residual stress | Radial clamping or opening stress from thermal mismatch, processing, or loading; it changes contact and hence slip resistance. |
| Geometry and constituents | Fibre radius, volume fraction/spacing, embedded length, fibre and matrix elastic properties, and fibre strength. These enter shear-lag and energy-balance reductions. |
| Interface state | Coating/interphase identity, roughness, wear/damage, humidity/oxidation, temperature, cycle count, and accumulated slip. Treating these as constant when evidence shows evolution is an approximation. |

The 1990 energy-balance treatment relates the debond work \(\Gamma_d\) to a
critical debond shear stress and a *separate* frictional sliding resistance,
with matrix shear modulus, fibre radius, and fibre-volume fraction in the
relation. [Sutcu and Hillig (1990)](https://doi.org/10.1016/0956-7151(90)90278-O)
The interface review by Evans, Zok, and Davis similarly treats debond energy
and sliding resistance as independent mechanical parameters. [Evans, Zok, and
Davis (1991)](https://doi.org/10.1016/0266-3538(91)90010-M)

Push-out tests can estimate parameters, but their reduction is model-bound:
NASA describes the peak load as a debond indicator and a later steady load as
sliding friction, using a uniform-interfacial-shear assumption in the derived
stress. That is useful experiment-to-model evidence, not a universal friction
law. [Bansal et al., NASA report (1995)](https://ntrs.nasa.gov/citations/19960000619)

## Constitutive choices and their limits

A first model must choose, rather than conflate, at least these alternatives:

1. **Initially unbonded interface with contact/friction.** This may slip from
   the outset under residual clamping pressure; no debond-growth variable is
   implied.
2. **Initially bonded interface plus irreversible debond evolution.** A
   fracture criterion and \(\Gamma_d\) (or equivalent) determines the debond,
   followed by a distinct contact/friction law on the released segment.
3. **Sliding law.** Constant \(\tau_f\) is a deliberately limited shear-lag
   idealisation. Coulomb friction requires a normal-contact solution and a
   stick/slip rule. Roughness- or state-dependent laws require additional
   internal variables and their own identification data.

Hutchinson and Jensen analysed debonding/pullout under residual interface
compression using both constant-shear and Coulomb-friction idealisations. Their
model assumes a cylindrical cell, transversely isotropic fibre, isotropic
matrix, and Mode-II interface fracture; its closed forms are approximate.
[Hutchinson and Jensen (1990)](https://doi.org/10.1016/0167-6636(90)90037-G)
Finite-element studies have found that stick--slip/contact conditions and the
stress field near the debond tip limit simple analytical reductions.
[Hsueh (1996)](https://doi.org/10.1016/0921-5093(96)10196-9)

There is also direct evidence against assuming a permanent, material-wide
\(\tau_f\) or \(\mu\). NASA cyclic push-in work reports changes in sliding
stress and sliding distance with atmosphere, humidity exposure, cycling, and
interphase condition; NASA roughness work reports that larger displacements at
rough interfaces can involve interphase deformation rather than simple sliding.
[Eldridge, Bansal, and Bhatt, NASA (1998)](https://ntrs.nasa.gov/citations/19990007759)
[Eldridge et al., NASA (2002)](https://ntrs.nasa.gov/citations/20020072845)

## Implications for this pipeline

The current **prescribed bridging traction** tracer should not be relabelled
as frictional slip: it has neither a resolved fibre--matrix interface nor
tangential relative displacement, contact pressure, debond-front evolution,
or a frictional dissipation state. A reversible Mode-I traction--separation
law likewise cannot represent frictional slip merely by softening in the
normal direction.

A credible later resolved-slip slice would need:

1. Fibre, matrix, and interphase/interface geometry (or a clearly declared
   homogenised unit-cell model), plus a tangential kinematic measure.
2. A nonpenetration/contact convention in compression, normal-pressure model,
   and an explicit stick/slip complementarity or regularisation choice.
3. A separate debond evolution law and post-debond friction law, with internal
   state/restart provenance when either evolves with slip, cycles, environment,
   or wear.
4. Fibre bridging and fracture criteria that are independent of interface
   state, followed by a pullout representation only if fractured fibre segments
   and embedded lengths are modelled.
5. Verification for elastic stick, slip onset, constant-pressure sliding,
   debond advance, unloading/reloading, energy balance (including frictional
   dissipation), mesh/contact convergence, and sensitivity to the chosen
   regularisation. A bulk-only \(J\)-contour diagnostic is not automatically
   path independent when frictional contact and irreversible interface motion
   occur.

Until those ingredients and system-specific test data exist, the truthful
claim is a fixed-crack bridging study with frictional slip excluded—not a
predictive model of CMC interfacial sliding, pullout toughness, or composite
failure.

## Primary sources

- B. Budiansky, J. W. Hutchinson, and A. G. Evans, *Matrix fracture in
  fiber-reinforced ceramics* (1986), *Journal of the Mechanics and Physics of
  Solids* 34(2), 167–189. [DOI](https://doi.org/10.1016/0022-5096(86)90035-9),
  [author-hosted paper](https://web-static-aws.seas.harvard.edu/hutchinson/papers/382.pdf).
- D. B. Marshall and A. G. Evans, *Failure Mechanisms in Ceramic-Fiber/
  Ceramic-Matrix Composites* (1985), *Journal of the American Ceramic Society*
  68(5), 225–231. [DOI](https://doi.org/10.1111/j.1151-2916.1985.tb15313.x).
- A. G. Sutcu and W. B. Hillig, *The effect of fibre–matrix debond energy on
  the matrix cracking strength and the debond shear strength* (1990), *Acta
  Metallurgica et Materialia* 38(12), 2653–2662.
  [DOI](https://doi.org/10.1016/0956-7151(90)90278-O).
- A. G. Evans, F. W. Zok, and J. Davis, *The role of interfaces in
  fiber-reinforced brittle matrix composites* (1991), *Composites Science and
  Technology* 42, 3–24. [DOI](https://doi.org/10.1016/0266-3538(91)90010-M).
- J. W. Hutchinson and H. M. Jensen, *Models of fiber debonding and pull-out
  in brittle composites with friction* (1990), *Mechanics of Materials* 9(2),
  139–163. [DOI](https://doi.org/10.1016/0167-6636(90)90037-G),
  [author-hosted paper](https://groups.seas.harvard.edu/hutchinson/papers/409.pdf).
- C. H. Hsueh, *Analysis of debonding and frictional sliding in fibre-reinforced
  brittle matrix composites: basic problems* (1996), *Materials Science and
  Engineering A* 212, 75–86. [DOI](https://doi.org/10.1016/0921-5093(96)10196-9).
- R. E. Bansal et al., *Interfacial Bonding and Friction in SiC-Filament-
  Reinforced Ceramic- and Glass-Matrix Composites* (NASA report, 1995).
  [NTRS record](https://ntrs.nasa.gov/citations/19960000619).
- R. L. Tripp, *Continuous Fiber Ceramic Matrix Composites for Heat Engine
  Components* (NASA report, 1988). [NTRS record](https://ntrs.nasa.gov/citations/19880013027).
- J. I. Eldridge, N. P. Bansal, and R. T. Bhatt, *Evolution of Interfacial
  Sliding Stresses During Cyclic Push-in of SiC Fibers in a BMAS Glass-Ceramic
  Matrix* (NASA report, 1998). [NTRS record](https://ntrs.nasa.gov/citations/19990007759).
- J. I. Eldridge et al., *Influence of Interfacial Roughness on Fiber Sliding
  in Ceramic Matrix Composites* (NASA report, 2002).
  [NTRS record](https://ntrs.nasa.gov/citations/20020072845).

# Research note: mortar versus contact formulation for crack analysis

## Scope and terminology correction

This note distinguishes **mortar**, **contact**, and **fracture evolution** for
finite-element crack analysis, with emphasis on an effective crack plane or a
resolved fibre--matrix interface in a ceramic-matrix composite (CMC). It does
not change the current fixed-crack prescribed-bridging tracer.

The proposed choice is not between two equivalent physical models. **Contact**
is a unilateral (and optionally frictional) interface condition. **Mortar** is
a face-to-face interface discretisation and constraint-enforcement technique
that can be used *for contact*. For example, MOOSE exposes frictionless,
glued, and Coulomb contact models, and separately permits face-to-face contact
using a mortar method. [MOOSE, *Contact*](https://mooseframework.inl.gov/syntax/Contact/index.html)
MOOSE's mortar contact implementation uses lower-dimensional Lagrange
multipliers to enforce the contact constraints; the normal multiplier has the
meaning of contact pressure. [MOOSE, *Step 2 -- Mortar Contact*](https://mooseframework.inl.gov/modules/contact/tutorials/introduction/step02.html)

Accordingly, the useful formulation question is:

> Which contact enforcement should act when the two already-declared surfaces
> close, and which separately declared law creates, damages, or advances the
> crack/interface?

## What each mechanism represents

| Mechanism | Physical/numerical role | It can establish by itself | It cannot establish by itself |
| --- | --- | --- | --- |
| Node/face or other conventional contact | Enforces a normal no-penetration condition and may add friction on a declared pair of surfaces. | Closure and, if parameterised, post-closure frictional sliding of an existing crack or debond. | A tensile bond, debond initiation, irreversible separation damage, or new crack geometry. |
| Mortar contact | Enforces that same contact problem with a face-to-face interface discretisation; often uses multiplier variables on an interface mesh. | More directly resolved contact pressure/constraint fields on nonmatching faces, subject to the solver's implementation and convergence checks. | The same fracture mechanisms above; mortar alone supplies no traction--separation damage history or crack-growth criterion. |
| Cohesive interface / cohesive contact | Supplies traction versus separation and, when declared, damage initiation and damage evolution. Contact may be combined to handle closure after separation. | Delamination/debonding of a *predeclared* interface or effective crack plane, within its chosen law and parameters. | Spontaneous arbitrary-path cracking unless paired with an enrichment, remeshing, phase-field, or other geometry-evolution method. |
| Crack-growth method (for example XFEM with cohesive or LEFM criteria) | Adds a rule that changes crack geometry or crack-front position. | Crack initiation/propagation only for the stated criterion, material law, and admissible path representation. | Calibration, material qualification, or the full CMC sequence of debonding, sliding, fibre fracture, and pullout without those mechanisms being separately modelled. |

The contact distinction is explicit in MOOSE: its node/face method searches for
secondary nodes penetrating primary faces and constrains them against
penetration, while its mortar system is an alternative discretisation for
mechanical-contact constraints. [MOOSE, *Contact Module*](https://mooseframework.inl.gov/modules/contact/)
The same MOOSE tutorial reports tighter constraint enforcement and improved
contact-pressure quality for its mortar example, but also labels its 3-D mortar
contact experimental and warns that edge-to-edge contact and edge dropping can
produce artifacts at sharp contact/no-contact transitions. That is an
implementation-specific limitation, not a universal guarantee for all mortar
methods. [MOOSE, *Step 2 -- Mortar Contact*](https://mooseframework.inl.gov/modules/contact/tutorials/introduction/step02.html)

## Crack closure is not crack creation

For a known crack, conventional or mortar contact is appropriate when the
analysis must prevent crack-face interpenetration under compression, and a
friction law is appropriate only if frictional sliding is a declared physical
assumption. In Abaqus' cracked-surface treatment, the pressure--overclosure
law acts while a crack is closed; cohesive normal traction contributes when it
is open, and friction can contribute to shear only after the cohesive response
has fully degraded. [Abaqus, *Contact Interaction of Cracked Element Surfaces*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEANLRefMap/simaanl-c-enrichment-contact-interaction.htm)
This is direct evidence for composing closure contact with a cohesive law,
rather than treating either contact enforcement choice as a debonding law.

Pure contact has no tensile adhesion/damage state. A contact interaction can
be made cohesive, but then the cohesive response is the fracture model, not
the underlying contact discretisation. Abaqus states that cohesive contact can
model a bonded interface, delamination through traction versus separation, and
progressive bond failure; it requires a damage-initiation criterion and a
damage-evolution law for the response to degrade. [Abaqus, *Contact Cohesive Behavior*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEITNRefMap/simaitn-c-cohesivebehavior.htm)
Without the evolution law, Abaqus evaluates an initiation criterion only for
output and does not damage the cohesive surfaces. [Abaqus, *Contact Cohesive Behavior*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEITNRefMap/simaitn-c-cohesivebehavior.htm)

## Composite and interface-fracture boundary

For a CMC, the interface must be named before selecting an enforcement method:

- An **effective crack plane** is a reduced model of matrix-crack opening. A
  cohesive law there does not resolve individual fibres or fibre--matrix
  geometry.
- A **resolved fibre--matrix interface** may use cohesive damage to represent
  adhesion loss and contact/friction after separation. It still needs its own
  strength, work-of-separation, mixed-mode, unloading, and friction choices.
- **Frictional slip** is not synonymous with debonding. The original CMC
  micromechanics analysis by Budiansky, Hutchinson, and Evans distinguishes
  initially unbonded interfaces that slide frictionally from weakly bonded
  interfaces that debond near a matrix crack. [Budiansky, Hutchinson, and
  Evans, *Matrix Fracture in Fiber-Reinforced Ceramics* (1986)](https://web-static-aws.seas.harvard.edu/hutchinson/papers/382.pdf)
- NASA's CMC overview lists matrix cracking, interface debonding, relative
  sliding, intact-fibre bridging, fibre fracture, and pullout as distinct
  toughening mechanisms. Thus neither a contact constraint nor mortar
  enforcement alone warrants a claim to the whole mechanism sequence.
  [NASA, *Toughening Mechanisms in Ceramic Matrix Composites*](https://ntrs.nasa.gov/citations/19880013027)

If a predeclared interface is the intended fracture path, the central model
decision is a cohesive law plus closure/contact behavior. In Abaqus, cohesive
surfaces use a linear traction--separation response before damage and a scalar
damage variable that evolves from zero to one after the declared criterion is
met; compressive stiffness is not degraded by that cohesive damage variable.
[Abaqus, *Contact Cohesive Behavior*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEITNRefMap/simaitn-c-cohesivebehavior.htm)
That division is compatible with using mortar contact for the compression
constraint if the chosen solver supports that composition, but mortar does not
replace the cohesive state law.

## When neither alone represents initiation or propagation

Neither conventional contact nor mortar contact represents crack initiation or
progression merely because two surfaces are available to the solver. Both
presuppose a contactable interface/surface and enforce its kinematics when it
closes. Cohesive behavior adds degradation on that interface but still fixes
the potential path unless the discretisation itself can create/extend the
discontinuity.

For example, Abaqus describes XFEM cohesive behavior as having initially
linear traction--separation response followed by damage initiation and
evolution, and separately provides an XFEM LEFM approach for studying crack
initiation and propagation. [Abaqus, *Choosing the Type of XFEM Analysis*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAECAERefMap/simacae-c-engconcxfemtype.htm)
The relevant limitation is therefore not a solver defect: a model must declare
all of (1) the candidate fracture surface/path, (2) initiation, (3) evolution
or geometry update, (4) closure/contact, and (5) tangential post-separation
behavior when applicable.

## Decision conditions for a future slice

| Declared problem | Formulation consequence | Required proof beyond a successful solve |
| --- | --- | --- |
| Fixed, always-open Mode-I tracer with prescribed bridging traction | Neither contact nor mortar is necessary unless compression/closure is in scope. | Face-pairing, opening convention, traction-work bookkeeping, mesh sensitivity. |
| Fixed crack that may close, friction explicitly excluded | Add frictionless normal contact; use mortar only if face-to-face constraint/pressure accuracy is needed and supported. | No-interpenetration under closure and no artificial tensile traction after reopening. |
| Fixed crack that may close and slide after a declared adhesion loss | Combine an irreversible cohesive law with normal contact and a separately parameterised friction law. Mortar is a possible contact-enforcement choice. | Initiation, unload/reload, complete failure, closure, slip, energy balance, and restart-history tests. |
| Predeclared fibre--matrix interface debonding | Model the resolved interface with cohesive damage and post-debond contact/friction as justified; mortar may improve interface constraint transfer on nonmatching faces. | Interface geometry/provenance, mixed-mode law, calibration, mesh-objective dissipation, and mechanism-separation tests. |
| Crack initiation or an advancing crack front outside a predeclared interface | Add a declared crack-evolution representation (for example enrichment, remeshing, or phase field) and couple any contact after faces exist. | Benchmark against an analytical/reference fracture case; path, increment, and mesh sensitivity; do not label it a material prediction without independent evidence. |

## Conclusion

For a crack that already exists, **contact physics** answers what happens under
closure, while **mortar** answers one way of enforcing that contact across
faces. For adhesion loss or delamination, the necessary additional object is
an irreversible cohesive/interface law; for an advancing crack, it is a
geometry-evolution rule. The terms should remain separate in the project:
call the method **mortar contact** when describing enforcement, **contact**
when describing closure/friction physics, and **cohesive damage/debonding** or
**crack propagation** only when their respective state/evolution laws are
actually declared and verified.

## Sources

- MOOSE, [*Contact Module*](https://mooseframework.inl.gov/modules/contact/).
  Official framework documentation for node/face and mortar contact.
- MOOSE, [*Step 2 -- Mortar Contact*](https://mooseframework.inl.gov/modules/contact/tutorials/introduction/step02.html).
  Official mortar-contact implementation tutorial and stated limitations.
- Abaqus, [*Contact Cohesive Behavior*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEITNRefMap/simaitn-c-cohesivebehavior.htm).
  Official cohesive-contact/damage documentation.
- Abaqus, [*Contact Interaction of Cracked Element Surfaces*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAEANLRefMap/simaanl-c-enrichment-contact-interaction.htm).
  Official crack-closure, cohesive, and friction interaction documentation.
- Abaqus, [*Choosing the Type of XFEM Analysis*](https://docs.software.vt.edu/abaqusv2025/English/SIMACAECAERefMap/simacae-c-engconcxfemtype.htm).
  Official crack-initiation/propagation capability boundary.
- B. Budiansky, J. W. Hutchinson, and A. G. Evans, [*Matrix Fracture in
  Fiber-Reinforced Ceramics* (1986)](https://web-static-aws.seas.harvard.edu/hutchinson/papers/382.pdf), *Journal of the Mechanics and Physics of Solids* 34, 167--189, [DOI](https://doi.org/10.1016/0022-5096(86)90035-9).
- NASA, [*Toughening Mechanisms in Ceramic Matrix Composites*](https://ntrs.nasa.gov/citations/19880013027).

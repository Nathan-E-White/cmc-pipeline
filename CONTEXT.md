# CMC Fracture Pipeline

This context describes a workflow that compares a high-fidelity CMC-fracture simulation with a learned acceleration model.  Its terms separate physical outputs, numerical reference evidence, and permissible surrogate use.

## Language

**Reference solution**:
The finite-element result for a declared input, constitutive model, discretization, and solver configuration.  It is a comparison authority within that model, not experimental truth or a qualified structural prediction.
_Avoid_: ground truth, exact solution

**Surrogate**:
A learned approximation to selected reference-solution outputs over a bounded input domain.
_Avoid_: solver replacement, physics engine

**Reference corpus**:
An immutable, declared collection of accepted reference Field Sets with compatible
problem-card evidence and a full-case training/held-out split. It is training
input evidence, not a collection of arbitrary mesh nodes or quadrature points.
_Avoid_: dataset (when membership, split, and evidence identity are material)

**Provenance closure**:
The verified transitive chain from declared reference evidence through a frozen
reference corpus, recipe/runtime, model release, export/parity receipt, and a
derived experimental surrogate observation or projection. Byte identity alone
does not establish provenance closure.
_Avoid_: checksum chain, validated lineage

**Model release**:
A digest-addressed experimental surrogate artifact with its frozen corpus,
problem-card, recipe/runtime, weights, held-out metrics, limits, model card,
and declared export availability. It does not decide a reference run outcome.
_Avoid_: approved model, solver version

**Inference package**:
A browser- or runtime-compatible, digest-addressed export of one model release
with declared tensor/unit contracts, transforms, applicability fingerprint, and
parity receipt. Its use remains experimental and case-bound.
_Avoid_: model download, frontend solver

**Workflow submission receipt**:
The immutable record that a compiled workflow digest was acknowledged by a
declared execution target, including its target identity and observation cursor.
It establishes neither execution completion nor a reference numerical outcome.
_Avoid_: run result, scheduler acceptance

**Fracture quantity**:
A declared crack-driving output, such as a contour- or domain-evaluated $J$-integral, with the assumptions and numerical details required to interpret it.
_Avoid_: toughness (unless material-property identification is established)

**Adjudication**:
The recorded comparison of a surrogate prediction with reference evidence and declared acceptance criteria.
_Avoid_: validation (unless appropriate independent physical evidence is included)

**Indeterminate case**:
A case for which the surrogate does not satisfy declared domain, quality, or agreement criteria and cannot yield an accepted screening result.
_Avoid_: pass with warning

**Prescribed bridging traction**:
A declared crack-face closure load used to explore a fixed-crack numerical tracer. It represents neither resolved fibres nor a calibrated interface, and does not evolve with crack opening.
_Avoid_: fibre bridging law, interface model

**Paired crack faces**:
The two distinct, matching mesh traces created by opening one declared crack
trace, together with an auditable one-to-one correspondence in their reference
configuration and a declared normal-opening convention.  A physical group that
merely contains both faces is not, by itself, a paired-crack-face contract.
_Avoid_: crack faces (when correspondence is required), interface map

**Mortar interface coupling**:
A weak interface discretization that transfers a declared constraint or traction
between overlapping primary and secondary traces, including nonmatching meshes.
It does not specify whether the interface is bonded, cohesive, or in contact.
_Avoid_: contact law, crack-growth law

**Mechanical contact formulation**:
A unilateral nonpenetration constraint, with a declared normal enforcement
method and optional tangential friction or stick--slip law. It governs closed
or reclosed faces; it neither initiates nor advances a crack by itself.
_Avoid_: mortar coupling, cohesive damage, crack propagation

**Cohesive interface quadrature**:
Integration of a declared traction--separation response over paired crack-face
line elements using a single reference coordinate and consistent weights.  It
is an effective crack-plane construction, not evidence of a resolved
fibre--matrix interface.
_Avoid_: contact formulation, fibre interface (unless that geometry is resolved)

**Opened crack mesh artifacts**:
The coupled mesh, mesh audit, and independently validated crack-face-pair map
for one declared opened-crack case.  Their shared identity is required before
an opening-dependent interface response may be assembled.
_Avoid_: mesh file, physical group, solver-private pairing state

**Displacement-controlled loading**:
A declared monotonic boundary-displacement program whose reaction is observed.
It is distinct from a fixed traction and is used when the model's tangent may
soften under continued opening.
_Avoid_: load-controlled solve, fixed traction

**Reversible interface potential**:
Stored energy associated with a history-free traction--separation response at
the current opening.  It is recoverable on unloading and is not toughness,
fracture energy, or dissipated work.
_Avoid_: Gc, cohesive fracture energy, energy release rate

**Irreversible cohesive damage**:
A nondecreasing constitutive state on a declared interface or effective crack plane that reduces tensile cohesive traction according to loading history. It requires explicit unloading/reloading and complete-failure rules.
_Avoid_: reversible softening, debonding

**Debonding**:
Physical loss of adhesion along a fibre--matrix interface, with separately declared initiation and propagation conditions. It may produce an irreversibly damaged cohesive interface, but it is not itself fibre fracture, pullout, or frictional slip.
_Avoid_: cohesive damage, fibre failure

**Frictional slip**:
Relative tangential motion between surfaces under a declared contact and friction law, commonly along a debonded fibre--matrix interface. It is post-adhesion-loss dissipation, not debonding itself, and cannot be represented by a normal cohesive-damage variable alone.
_Avoid_: debonding, cohesive softening, prescribed bridging traction

**Fibre fracture**:
Loss of load-carrying continuity of a reinforcing fibre through a declared fibre-failure criterion. It is distinct from matrix cracking, interface debonding, frictional slip, and pullout.
_Avoid_: fibre failure, composite failure

**Crack propagation**:
A change in the declared crack geometry or crack-front position produced by a declared evolution rule. A fixed crack can have a crack-driving diagnostic, but it does not propagate.
_Avoid_: crack growth (unless the loading mechanism is named), advancing J contour

**Fatigue crack growth**:
Crack propagation under declared cyclic loading, reported against cycle count with an explicit loading-ratio convention and propagation criterion. It is distinct from monotonic fracture and time-dependent environmentally assisted crack growth.
_Avoid_: crack growth (without a loading qualifier), fatigue life

**Thermal loading descriptor**:
A declared temperature, gradient, heat flux, or thermal-cycle input that characterises a case but does not by itself establish a solved temperature field or thermal stresses.
_Avoid_: thermal analysis, thermomechanical result

**Thermomechanical coupling**:
The declared dependence between a solved temperature field and mechanical response, including thermal strain and any stated temperature-dependent material or interface state. It is distinct from merely attaching a thermal loading descriptor to a mechanical case.
_Avoid_: thermal correction, thermal failure mode

**Thermally assisted failure**:
Failure whose initiation or evolution depends jointly on thermal history and a separately declared mechanical, chemical, or time-dependent mechanism. It may involve residual stress, creep, oxidation, or interface degradation, but is not a single material mechanism.
_Avoid_: thermal failure, heat damage

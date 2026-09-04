# PINN architectures for the CMC fracture work

**Audience:** CMC Pipeline maintainers  
**Date:** 3 September 2026  
**Scope:** Architecture choices for the repository's present and credible next
fracture problems. This is a numerical-method research note, not material
qualification or a recommendation to replace the reference solver.

## Executive answer

For the current fixed, opened crack, the defensible PINN is an **enriched,
energy-based, two-region displacement network**. It should use the existing
audited paired-face map as an interface contract, represent the displacement
jump explicitly, and retain a small crack-tip asymptotic enrichment. A vanilla
smooth-coordinate PINN is the wrong basis: it is being asked to approximate a
jump and a near-tip singularity with a globally smooth function, which is a
rather expensive way to rediscover why XFEM has enrichment functions.

For the present prescribed-bridging tracer, this architecture is useful as a
*reference-constrained field reconstruction or inverse load-identification
experiment*, not as a production forward solver. For the reversible cohesive
tracer, add the declared traction-separation potential as a paired-face
quadrature term. For a later irreversible law, add a non-healing history state
and solve incrementally. Do not reach for a phase-field PINN unless the scope
has changed to crack initiation or changing topology. For many-case rapid
inference, train a mesh-aware operator surrogate from accepted FEM field sets;
that is a different product from a PINN.

## What the existing cases actually are

The current case card is a two-dimensional plane-strain plate with one fixed,
straight, pre-opened crack. It declares a deterministic correspondence between
the two crack faces, a normal-opening convention, a synthetic reversible
Mode-I bilinear law, displacement control, and a diagnostic domain integral.
It explicitly excludes contact, compression, friction, irreversible damage,
crack advance, fibre-interface resolution, and calibrated material claims.

Those distinctions are architectural inputs:

| Repository problem | Kinematic/numerical fact | Appropriate learned formulation | Do not claim |
| --- | --- | --- | --- |
| V1 opened elastic crack | Strong displacement jump; LEFM-like tip field | Two region nets plus signed-distance/jump feature and crack-tip enrichment; equilibrium or potential-energy loss | Calibrated CMC response or crack advance |
| V2 prescribed bridging | Fixed geometry and a known distributed closure load | Same field representation; the known traction enters external work | A cohesive law, fibre bridging, or debonding |
| V2 reversible cohesive tracer | Paired faces and a history-free normal opening | Deep-energy objective with the declared interface potential integrated over the pair map | Fracture energy, toughness, dissipation, or physical validation |
| Future irreversible effective crack plane | Opening jump plus a nondecreasing internal state | Incremental cohesive deep-energy PINN, state carried between increments | Fibre-matrix debonding unless geometry, data, and verification warrant it |
| Future nucleation/path/branching | Crack topology changes | Phase-field/deep-Ritz or nonlocal/peridynamic formulation | A sharp-crack cohesive calculation without a separate interface model |
| Many accepted cases, fast screening | Map from case description to field/quantity | Mesh-aware neural operator or graph operator trained on the reference corpus | Physics-only extrapolation or automatic design authority |

## Recommended architecture: fixed sharp crack

Let `s(x)` be a signed distance to the declared crack trace, and let
`H(s)` distinguish its lips. For a fixed crack, parameterize displacement as

\[
u_\theta(x) = u^{(0)}_\theta(x)
  + H(s(x))u^{(J)}_\theta(x)
  + \chi_{tip}(x)\sum_k a_k\Phi_k^{tip}(r,\phi).
\]

`u^(0)` is a smooth bulk network, `u^(J)` is a jump network, and the last term
is a compactly supported analytical crack-tip enrichment. Equivalent practical
implementations are (a) two independently parameterized regional displacement
nets whose traces are evaluated from the known lip pairing, or (b) a
discontinuity-embedded input feature plus separate smooth/jump heads. The
first version is easiest to audit against this repository's public pairing
artifact; the second is convenient where the signed-distance geometry is
reliable.

For linear elasticity, prefer a variational/deep-energy loss over a raw
second-derivative residual:

\[
\Pi_\theta = \int_{\Omega\setminus\Gamma}
  \tfrac12\epsilon(u_\theta):C:\epsilon(u_\theta)\,d\Omega
  - W_{ext}(u_\theta) + \Pi_\Gamma.
\]

Essential displacement conditions should be imposed exactly through an output
transform where practical, rather than merely penalized. Sample integration
densely in a tip annulus and around the cohesive zone, use the same reference
configuration and quadrature orientation as the paired-face artifact, and
evaluate the result on held-out FEM field sets plus the existing mesh-refinement
checks. Enriched PINNs have specifically demonstrated the benefit of including
crack-tip asymptotic functions for two-dimensional in-plane crack analysis;
discontinuity-embedded deep-energy methods use geometry-derived discontinuous
features for strong and weak discontinuities.

## Cohesive extension

For the current reversible law, the interface term is simply

\[
\Pi_\Gamma = \int_{\Gamma}
 \psi\!\left(\delta_n\right)\,d\Gamma,
\quad \delta_n=(u^+-u^-)\cdot n_{-\to+},
\quad t_n=\partial\psi/\partial\delta_n.
\]

The `+` and `-` traces must be taken at matched locations supplied by
`opened-crack-face-pairs/v1`; nearest-neighbour points in a deformed field are
not a constitutive interface. The present law is recoverable, so its first-load
area must remain labelled *reversible interface potential*, exactly as the
case card does.

For a later irreversible extension, train per displacement increment and
carry a declared state, for example `kappa_n=max(kappa_(n-1), delta_eff)`, into
the next step. The state needs its own artefact identity, restart test,
unloading/reloading test, complete-failure test, and energy partition. Recent
cohesive PINN work uses precisely this pattern—an explicit jump feature,
cohesive energy in the objective, incremental loading, and history updates—but
it is evidence of a numerical method, not of this CMC system's parameters.

## Architectures that are not substitutes for one another

### 1. Standard residual PINN

One network maps `(x,y)` to displacement and minimizes equilibrium, boundary,
and data penalties. It is a useful baseline and a reasonable inverse method on
a smooth, uncracked subdomain. It is not the recommended sharp-crack model:
loss weights compete, derivatives magnify stiffness, and the representation
does not encode a jump. Gradient-pathology research documents the imbalance
between loss terms; fracture adds singular and discontinuous fields on top.

### 2. Enriched/decomposed PINN or deep-energy PINN — recommended now

This is the sharp-crack architecture above. It retains an explicit geometry
contract, makes the two traces observable, and can consume the current
mesh/pair artefact directly. It is the smallest credible PINN research slice:
keep material, geometry, and loading fixed; learn one field; compare against
the accepted reference solution; report displacement, traction and energy
residuals—not just a visually plausible stress map.

### 3. Cohesive deep-energy PINN — recommended only after the first slice

Add the interface potential to the energy functional and, later, a history
state. The method aligns structurally with the current paired-lip quadrature.
It also inherits every difficulty of softening equilibrium: nonconvexity,
increment selection, path dependence, and local resolution. It should not be
introduced before the enriched fixed-crack elastic slice closes.

### 4. Phase-field/deep Ritz PINN — a future propagation lane

Use separate networks for displacement and a regularized damage/phase field,
with alternate minimization or a carefully controlled coupled objective and
irreversibility. This can represent nucleation, kinking, branching and
coalescence, but replaces the repository's explicit open-face/pair contract
with a diffuse crack and introduces a length scale. It answers a different
question, not a cheaper version of the current cohesive calculation.

### 5. Neural operator — the deployment lane, not a PINN

DeepONet-style branch/trunk networks and mesh/graph operators learn a
case-to-field map after training on a bounded corpus. They are appropriate once
there are many accepted reference Field Sets across load, geometry and material
parameters. They require declared representation and coverage; they do not
derive credibility from putting PDE residuals in a loss. The existing
reference-corpus/model-release/provenance language is therefore the correct
operating boundary.

## Smallest defensible experiment

1. Freeze one V1 elastic edge-crack card and its three mesh levels; use the
   medium mesh only for development and reserve fine results for evaluation.
2. Implement the two-region, tip-enriched displacement ansatz with exact
   boundary transforms and energy quadrature. Feed the crack trace and the
   audited pair map as immutable geometry evidence.
3. Compare displacement and strain-energy error away from the tip, face-opening
   error along matched pairs, reaction balance, and the two declared domain
   integral radii. Make no toughness claim.
4. Repeat with V2 prescribed bridging. Only after those checks pass, add the
   reversible interface potential and reproduce the current continuation
   programme.
5. If this is intended for fast repeated inference, stop solving a PINN per
   case and use its validated outputs to design a corpus-backed operator model.

## Decision

Build **one enriched deep-energy, paired-lip PINN research prototype** for the
V1 fixed-crack elastic problem. Its success condition is agreement with the
declared FEM reference under an explicit error and applicability contract.
Extend it to reversible cohesion only after it reproduces paired opening and
bulk equilibrium. Keep irreversible cohesion, physical CMC debonding, crack
growth, and a deployable neural operator as separate slices. This has the small
virtue of not asking a neural network to quietly supply four missing mechanics
models.

## Evidence and limitations

- [Gu et al., *Enriched physics-informed neural networks for 2D in-plane crack analysis* (2023)](https://doi.org/10.1016/j.ijsolstr.2023.112321) supplies the sharp-crack enrichment precedent. Its benchmarks support the representation choice, not CMC calibration or cohesive propagation.
- [Zhao and Shao, *DENNs: Discontinuity-Embedded Neural Networks for fracture mechanics* (2025)](https://doi.org/10.1016/j.cma.2025.118184) and the authors' [DEDEM preprint (2024)](https://arxiv.org/abs/2407.11346) support explicit geometry-derived discontinuity features in energy formulations. The peer-reviewed article should be preferred when reproducing implementation details.
- [Cheng et al., *Physics informed neural networks for interfacial debonding analysis* (2026)](https://doi.org/10.1016/j.engfracmech.2026.112441) supports the cohesive deep-energy/history-state architecture. It is recent numerical literature, not an independently reproduced result here.
- [Goswami et al., *Transfer learning enhanced PINN for phase-field fracture* (2020)](https://doi.org/10.1016/j.tafmec.2019.102447) and [Manav et al., *Phase-field modeling of fracture with physics-informed deep learning* (2024)](https://doi.org/10.1016/j.cma.2024.117104) support phase-field/deep-Ritz approaches for diffuse crack evolution; that modelling choice is outside the present fixed-interface scope.
- [Wang, Teng and Perdikaris, *Understanding and mitigating gradient pathologies in PINNs* (2021)](https://doi.org/10.1137/20M1318043) supports caution about composite PINN-loss optimization. It does not prove a fracture-specific performance limit.
- [Lu et al., *Learning nonlinear operators via DeepONet* (2021)](https://doi.org/10.1038/s42256-021-00302-5) establishes the operator-learning distinction used here. It does not establish performance for arbitrary crack topologies.

Research stopping point: the evidence is sufficient to distinguish the
architectures and make the scoped recommendation. No source establishes that a
PINN will beat the pinned DOLFINx reference solver on this one-case problem;
that would need the proposed controlled benchmark.

# Research note: CMC fracture surrogate theory

## Scope inferred from the repository

The only substantive project specification is the draft Argo workflow
[`cmc-fracture-dag.yaml`](../.argo/cmc-fracture-dag.yaml).  It describes a
voxel-mesh input, a high-fidelity finite-element (FE) calculation of a
J-integral, a parallel Fourier neural operator (FNO) inference track, and an
adjudication step.  This note therefore treats the intended subject as
**parametric fracture analysis of ceramic-matrix composites (CMCs), with FE
fields as the reference and an FNO-derived surrogate as an acceleration**.  It
does not treat the empty containers or the workflow's internal image names as
evidence that a solver, material model, training corpus, or validation process
already exists.

## Physics and fracture-mechanics basis

1. **Relevant CMC failure is progressive, not monolithic ceramic rupture.** In
   tensile tests of unidirectional SiC-fibre/glass-ceramic material, Marshall
   and Evans observed multiple matrix cracking followed by fibre fracture and
   pull-out, and identified the importance of frictional fibre--matrix bonding.
   This supports making matrix cracks, interfaces, and bridging/pull-out
   parameters explicit model inputs rather than representing the CMC as a
   homogeneous brittle solid. [Marshall & Evans (1985), original experimental
   paper](https://doi.org/10.1111/j.1151-2916.1985.tb15313.x).

2. **Bridging alters the driving force for matrix cracking.** Marshall, Cox,
   and Evans modelled matrix cracking in brittle-matrix fibre composites using
   a stress-intensity approach in which bridging fibres enter as closure
   tractions on the crack faces.  Accordingly, a credible CMC model needs a
   stated interface/bridging constitutive law and its calibration range; a
   macroscopic elastic field alone is insufficient. [Marshall, Cox & Evans
   (1985), original paper](https://doi.org/10.1016/0001-6160(85)90124-5).
   Budiansky, Hutchinson, and Evans then distinguished initially unbonded,
   frictionally slipping interfaces from initially weakly bonded interfaces
   that can debond under an advancing matrix crack—useful alternative baseline
   regimes for a CMC model. [Budiansky, Hutchinson & Evans (1986), original
   paper](https://doi.org/10.1016/0022-5096(86)90035-9).

3. **The J-integral supplies a well-defined crack-driving observable within
   stated assumptions.** Rice introduced a contour integral with the same value
   for paths around a notch/crack tip in elastic or deformation-theory
   elastic-plastic two-dimensional fields.  This is the mathematical basis for
   using a computed (J) as an energy-release-rate-like quantity, but its path
   independence is not a blanket guarantee in the presence of evolving
   damage, frictional contact, inelastic dissipation, or non-proportional
   loading. [Rice (1968), original paper](https://doi.org/10.1115/1.3601206).

4. **For FE output, a domain formulation is the natural numerical form.**
   Moran and Shih derived crack-tip flux integrals and associated domain
   representations from momentum and energy balance, specifically noting their
   compatibility with FE methods and their use for three-dimensional crack
   fronts.  The theory document should therefore define the contour/domain,
   crack-front direction, and convergence/path-independence checks used to
   report (J). [Moran & Shih (1987), original paper](https://doi.org/10.1016/0013-7944(87)90155-X).

## Surrogate-method basis

1. **An FNO approximates a solution operator, not one isolated FE result.**
   The original FNO work defines a learned map from functional parameter fields
   to PDE solutions, parameterising its kernel in Fourier space.  Thus the
   appropriate training target here is a family of FE solutions,
   
   \[
   \mathcal S: a=(\Omega,\chi_f,\chi_m,\chi_i,\mathbb C,\theta,\ell,\bar u)
   \mapsto (u,\varepsilon,\sigma,J),
   \]
   
   where the arguments encode geometry/microstructure, phase and interface
   fields, constitutive and fracture parameters, loading, and crack state.  It
   is not defensible to call a network an FNO surrogate until this input/output
   family and its training distribution are specified. [Li et al. (2020),
   original FNO paper](https://arxiv.org/abs/2010.08895); [Kovachki et al.
   (2023), theoretical treatment](https://www.jmlr.org/papers/v24/21-1524.html).

2. **Geometry representation is a central design decision.** Ordinary FNOs use
   FFTs and therefore assume rectangular, uniformly sampled grids.  That fits a
   genuine voxel field, but not an arbitrary unstructured FE mesh merely named
   “voxel.”  Geo-FNO was introduced specifically to map irregular physical
   geometry into a uniform latent grid and accepts meshes, point clouds, and
   design parameters.  The project must decide whether the canonical datum is
   a regular voxel raster (ordinary FNO) or an irregular FE geometry (a
   geometry-aware/operator-on-mesh approach). [Li et al. (2022), original
   Geo-FNO paper](https://arxiv.org/abs/2207.05209).

3. **Accuracy must be evaluated at fracture-relevant outputs, not just field
   norms.** The FNO literature demonstrates fast surrogate evaluation on its
   benchmark PDE families, but that does not establish accuracy for sharp crack
   fields, discontinuities, CMC interfaces, or (J).  The pipeline's
   `evaluate-accuracy-drift` task should therefore compare held-out FE and
   surrogate results using at least energy-norm/field errors, (J) error at
   each selected crack-front location, and a crack-initiation/propagation
   decision metric.  It should reject or flag predictions outside the
   microstructure, material, loading, and crack-state training support.  This
   is an application-specific requirement inferred from the above sources and
   the repository workflow, not a result established by FNO papers.

## Minimum theory choices to settle before implementation

- **Target physics:** quasi-static versus transient loading; small versus finite
  strain; 2-D, 3-D, or a 3-D crack front; and the crack representation
  (explicit discontinuity, cohesive zone, phase field, or another model).
- **CMC constitutive scope:** anisotropic fibre/matrix elasticity, interface
  debond/slip and friction, matrix damage, fibre failure, and any
  temperature/environment dependence.  Each omitted mechanism limits what
  “fracture” the model can claim to predict.
- **Reference solve:** weak form, boundary conditions, mesh/refinement policy,
  nonlinear solution tolerances, and the domain-integral implementation and
  verification procedure.
- **Surrogate contract:** canonical input grid/mesh, output fields and scalar
  functionals, training data-generation design, split by *case* rather than
  by neighbouring voxels, uncertainty/OOD rule, and the FE-fallback policy.

## Suggested literature-review spine for `theory.tex`

Use the four primary threads above in this order: (1) observed CMC failure and
interface-controlled bridging; (2) fracture mechanics and the J/domain
integral; (3) FE as the high-fidelity parametric reference; and (4) neural
operators/FNOs as conditional accelerators, with geometry compatibility and
fracture-specific validation as explicit open conditions.  That narrative is
brief, professional, and avoids the central category error: presenting a fast
field regressor as a validated fracture-propagation model.

## Direct-source bibliography

- Rice, J. R. (1968). *A Path Independent Integral and the Approximate Analysis
  of Strain Concentration by Notches and Cracks*. Journal of Applied Mechanics,
  35(2), 379–386. [DOI](https://doi.org/10.1115/1.3601206).
- Marshall, D. B., & Evans, A. G. (1985). *Failure Mechanisms in
  Ceramic-Fiber/Ceramic-Matrix Composites*. Journal of the American Ceramic
  Society, 68, 225–231. [DOI](https://doi.org/10.1111/j.1151-2916.1985.tb15313.x).
- Marshall, D. B., Cox, B. N., & Evans, A. G. (1985). *The Mechanics of Matrix
  Cracking in Brittle-Matrix Fiber Composites*. Acta Metallurgica, 33(11),
  2013–2021. [DOI](https://doi.org/10.1016/0001-6160(85)90124-5).
- Budiansky, B., Hutchinson, J. W., & Evans, A. G. (1986). *Matrix fracture in
  fiber-reinforced ceramics*. Journal of the Mechanics and Physics of Solids,
  34(2), 167–189. [DOI](https://doi.org/10.1016/0022-5096(86)90035-9).
- Moran, B., & Shih, C. F. (1987). *Crack tip and associated domain integrals
  from momentum and energy balance*. Engineering Fracture Mechanics, 27(6),
  615–642. [DOI](https://doi.org/10.1016/0013-7944(87)90155-X).
- Li, Z. et al. (2020). *Fourier Neural Operator for Parametric Partial
  Differential Equations*. [arXiv:2010.08895](https://arxiv.org/abs/2010.08895).
- Kovachki, N. et al. (2023). *Neural Operator: Learning Maps Between Function
  Spaces With Applications to PDEs*. JMLR 24(89), 1–97.
  [Article](https://www.jmlr.org/papers/v24/21-1524.html).
- Li, Z., Huang, D. Z., Liu, B., & Anandkumar, A. (2022). *Fourier Neural
  Operator with Learned Deformations for PDEs on General Geometries*.
  [arXiv:2207.05209](https://arxiv.org/abs/2207.05209).

# Research note: fatigue crack growth for the CMC fracture pipeline

## Scope and present boundary

This note addresses what the phrase **crack growth** would mean under cyclic
loading for this repository's future CMC-inspired work.  It does not change
the current reference case.  The executable reference path is an isotropic,
linear-elastic, plane-strain **fixed-crack** benchmark; V2 adds a prescribed
closure traction but still has no evolving interface state or crack advance.
It can therefore produce cyclic responses or a domain-integral diagnostic at
declared load points, but it cannot produce a fatigue-crack-growth rate.

The note uses public NASA technical reports and the official ASTM scope as
authoritative evidence.  The cited experiments concern particular material
systems, architectures, temperatures, environments, and specimen geometries.
They establish neither parameters nor a validation claim for this repository.

## What must be distinguished

- **Fixed-crack cyclic response**: repeated loading of an unchanged crack and
  unchanged constitutive state.  It may be useful for solver exercise, but
  there is no crack length history and hence no \(da/dN\).
- **Damage accumulation**: change in a state variable such as matrix-crack
  density, interface damage, sliding displacement, or fibre degradation.  It
  is not necessarily propagation of one tracked crack.
- **Fatigue crack growth**: a declared crack measure \(a\) changes with cycle
  count \(N\), so the model can report a rate \(da/dN\) over a declared cycle
  interval.  In 3-D, the measure must state whether it is crack-front position,
  projected area, an equivalent length, or another explicitly defined
  quantity.
- **Failure life**: cycles to a stated failure event.  It is a different
  output from a stable-growth curve, even if the same test records both.

ASTM E647 defines its conventional rate result in terms of the crack-tip
stress-intensity-factor range \(\Delta K\) under linear elasticity, but also
warns that residual stresses and shielding/closure affect interpretation and
are not incorporated in the classical applied \(\Delta K\).  That is a useful
reporting discipline, not an automatic CMC model: bridging, evolving
interfaces, friction, and environmental degradation make a unique
\(da/dN\)-versus-applied-\(\Delta K\) relation an assumption to test rather
than a property to inherit. [ASTM E647-24, official scope and significance]
(https://store.astm.org/e0647-24.html).

## CMC-specific evidence relevant to the model

1. **Cyclic CMC behaviour is material-system and environment dependent.** A
   NASA study of a Sylramic-iBN/MI SiC/SiC system at 1204 C varied stress,
   time, temperature, and oxidation across tensile creep, dwell-fatigue, and
   cyclic-fatigue experiments.  It reported time-dependent matrix-crack
   growth, and different failure regimes associated with oxidation-induced
   unbridged crack growth and fibre degradation.  A future model must not
   collapse temperature, dwell time, atmosphere, and load history into a
   generic ``fatigue'' flag. [Halbig et al., NASA record and report]
   (https://ntrs.nasa.gov/citations/20080006464).

2. **Damage should be observed as well as inferred from force history.** In
   a 2023 NASA high-cycle-fatigue investigation of melt-infiltrated SiC/SiC,
   the stated experiment used a specified R-ratio and frequency and combined
   runout/failure observations with DIC, acoustic emission, microscopy, and
   fractography.  This supports retaining the measurement method and
   observation cadence in experimental provenance, rather than treating an
   inferred scalar crack length as self-authenticating. [Almansour et al.,
   NASA HCF presentation]
   (https://ntrs.nasa.gov/citations/20230012492).

3. **Service-relevant cycling can involve coatings and exposure, not a bare
   laminate alone.** NASA's flexural study tested coated and uncoated woven
   SiC/SiC in air and steam at high temperature, then used microstructural
   examination to identify propagation and failure modes.  Whether a future
   pipeline excludes coatings and steam is a legitimate scope decision, but
   it must be explicit; the present fixed-crack benchmark makes neither
   representation. [Jaskowiak et al., NASA flexural-fatigue study]
   (https://ntrs.nasa.gov/citations/20170008116).

4. **A stress--life result is not interchangeable with a crack-growth law.**
   NASA's 2007 high-temperature programme reported endurance and scatter for
   three named CMCs under a particular cyclic exposure.  Such data can inform
   an eventual life-model data set, but it does not identify an evolving crack
   geometry or calibrate a \(da/dN\) law for another CMC. [Kalluri and Verrilli,
   NASA/TM-2007-214922]
   (https://ntrs.nasa.gov/citations/20070034700).

## Minimum model contract for an actual growth slice

A numerical fatigue-growth case needs inputs and outputs beyond the current
static case contract.

| Contract area | Minimum declaration |
| --- | --- |
| Cyclic loading | waveform or explicit \(P_{min}, P_{max}\), stress/load ratio \(R\), frequency, dwell times, cycle-block size, control mode, and termination condition |
| Environment | temperature history, atmosphere/steam or an explicit inert/ambient assumption, and any coating representation |
| State | crack geometry/front, irreversible cohesive/debond state if used, contact/friction state if used, and any degradation variables |
| Advance rule | initiation criterion, driving quantity and its extraction procedure, direction/extension update, maximum increment, and arrest rule |
| Observable | \(a(N)\) or another named front/area measure with units, \(da/dN\) reduction method, uncertainty or resolution limit, and the event that defines failure |
| Provenance | material system and architecture, constituent/interphase assumptions, calibration source, mesh and cycle-increment convergence, nonlinear tolerances, and artifact hashes |

The advance rule is the key seam.  A cohesive law with irreversible damage but
a fixed geometry can model *damage accumulation*; it becomes a crack-growth
model only when a declared failure/advance mechanism changes the crack set and
records that change against cycle count.  Conversely, advancing a geometric
crack with a Paris-type rule does not represent CMC bridging, debond, or
environmental effects unless those assumptions appear in its driving law and
calibration domain.

For a CMC-specific path, the project should choose one physical abstraction
per slice:

- an **effective matrix-crack plane** with irreversible cohesive damage and a
  clearly defined advance event; or
- a **resolved fibre--matrix-interface** model with separately declared
  debond, contact/friction, and fibre-failure rules.

The first is a bounded constitutive experiment.  The second is a materially
stronger micro-mechanical claim and requires geometry, parameter, and
verification evidence that the repository does not currently contain.  Neither
should be called a calibrated SiC/SiC fatigue model merely because its loading
is cyclic.

## Numerical and evidence gates

Before reporting a simulated rate curve, require all of the following.

1. **Cycle and mesh convergence.** Demonstrate that \(a(N)\), rate reduction,
   and any crack-driving output are insensitive within declared tolerances to
   mesh refinement, crack-front/domain-integral extraction settings, and
   cycle-block/advance increment.  The current two-contour static gate is
   necessary but insufficient once state evolves.
2. **Mechanism checks.** Show non-healing on unload/reload for an irreversible
   law; no unphysical interpenetration in compression if crack faces can close;
   and an energy/work accounting that separates reversible storage from damage,
   friction, and numerical dissipation.
3. **Limiting comparators.** Recover the linear-elastic fixed-crack response
   when growth and inelastic states are disabled.  If a LEFM growth benchmark
   is added, report it as a numerical comparator under its stated conditions,
   not as CMC validation or ASTM conformance.
4. **Experimental comparison discipline.** Hold out complete loading
   trajectories and specimens, not adjacent cycle samples from the same
   trajectory.  Report material architecture, temperature/environment, load
   history, crack-measurement method, and uncertainty alongside any comparison.
   NASA's use of multiple observation modes in the cited HCF study illustrates
   why a single force/displacement signal should not be overclaimed as direct
   damage observation.

## Consequences for a learned acceleration model

The existing surrogate concept maps declared case inputs to reference outputs.
For fatigue growth, the input is necessarily history-dependent.  A suitable
future reference trajectory is closer to

\[
(x_0, L_{0:k}, q_{0:k}) \mapsto (x_{k+1}, a_{k+1}, y_{k+1}),
\]

where \(x\) is the crack/interface state, \(L\) is the declared cyclic-load
block, \(q\) is the environment history, and \(y\) contains fields and
reported observables.  The model must either receive the state/history
explicitly or declare a recurrent/state-update mechanism.  A static FNO over
geometry and a single peak load cannot, by itself, establish fatigue-memory
behaviour.

Adjudication should therefore test held-out trajectories and report at least:
crack/front error over cycle count, rate error only where the rate estimator is
resolved, event error for initiation/arrest/failure, conservation/constraint
violations, and out-of-domain status.  A surrogate that predicts only a
domain-integral value at fixed geometry remains a screening surrogate for that
quantity, not a crack-growth predictor.

## Repository-facing conclusion

The next honest bridge from the V2 tracer to fatigue research is a
**cycle-resolved, fixed-geometry irreversible-state experiment**, labelled as
damage accumulation unless and until its contract includes a crack-advance
event and \(a(N)\).  It should preserve the current claim boundary: numerical
reference evidence within the declared model, not experimental truth,
qualification, component-life prediction, or a calibrated CMC law.  A later
growth slice can then add one explicit advance mechanism, its numerical gates,
and a source-specific experimental-comparison plan.

## Sources

- ASTM International, [E647-24: *Standard Test Method for Measurement of
  Fatigue Crack Growth Rates*](https://store.astm.org/e0647-24.html). Official
  current scope, reporting quantity, and cautions on shielding/closure.
- M. Halbig et al., [*Tensile Creep and Fatigue of Sylramic-iBN Melt-Infiltrated
  SiC Matrix Composites: Retained Properties, Damage Development, and Failure
  Mechanisms*](https://ntrs.nasa.gov/citations/20080006464), NASA Technical
  Reports Server, 2008. Material-system-specific high-temperature fatigue and
  damage observations.
- A. S. Almansour et al., [*High-Cycle Fatigue Behavior of SiC-based Ceramic
  Matrix Composites (CMCs) at High Temperatures*](https://ntrs.nasa.gov/citations/20230012492),
  NASA Glenn, 2023. Public experimental presentation describing loading and
  DIC/AE/microscopy/fractography observations.
- M. Jaskowiak et al., [*Flexural Fatigue Behavior of an EBC CMC Composite
  System In Air and Steam at High Temperature*](https://ntrs.nasa.gov/citations/20170008116),
  NASA Glenn, 2017. Coating/environment-sensitive flexural-fatigue study.
- S. Kalluri and M. J. Verrilli, [*Elevated Temperature Fatigue Endurance of
  Three Ceramic Matrix Composites*](https://ntrs.nasa.gov/citations/20070034700),
  NASA/TM-2007-214922, 2007. High-temperature endurance evidence and material
  scatter under its declared test conditions.

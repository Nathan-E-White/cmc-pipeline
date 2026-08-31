# Research note: thermal coupling and CMC failure modes

## Scope and claim boundary

This note identifies failure mechanisms that a future thermally coupled CMC
fracture model would need to represent or explicitly exclude.  It does not
turn the V1 fixture corpus, the fixed-crack bridging tracer, or the scalar
`thermal_gradient_c_per_mm` input into a thermomechanical solver.  In the
current repository that input is representative fixture metadata; the
reference tracer is linear-elastic and is deliberately not a CMC material
model.

The useful distinction is between a **thermal loading descriptor** (for
example, a reported gradient) and a **temperature field**.  A field requires
thermal boundary conditions, heat fluxes, geometry, and conductivity (usually
temperature- and damage-dependent).  Only after that field is resolved can a
mechanical calculation obtain thermal strain, typically
\(\varepsilon_{th}=\alpha(T-T_{ref})\), and combine it with imposed mechanical
loading and a declared initial residual-stress state.

## Evidence-backed failure modes

| Coupled chain | Observed or modelled consequence | Minimum state/evidence needed before it is modelled |
| --- | --- | --- |
| Processing cooldown or thermal cycle -> fibre/matrix/interphase CTE mismatch -> residual stress | Changes matrix-cracking initiation and interfacial debonding energy; it is not captured by a temperature label alone. | Reference temperature, processing/cooldown history or measured initial stress, phase-wise \(\alpha(T)\), elastic properties, and interphase geometry. |
| Through-thickness gradient + external load -> spatially varying thermal strain/stress | Produces a combined thermo-mechanical creep/fatigue/fracture problem rather than separable “thermal” and “mechanical” margins. | Transient or steady heat solution, mechanical load history, constraints, temperature-dependent stiffness/CTE, and a declared dwell/cycle schedule. |
| EBC/CMC thermal-property mismatch and thermal cycling -> surface cracking | Cracks can increase the driving force for mixed-mode interface delamination; coating modulus and thickness matter to the stress state. | Layer stack, thickness, elastic and thermal properties, interface law, heat-transfer boundary conditions, and cycle history. |
| Surface/interface crack paths + water vapour/oxygen -> bond-coat/interphase oxidation and reaction products | Interface adhesion can fall, then delamination/spallation can expose the CMC; for fibre interphases, oxidation can change crack deflection/pull-out into strong bonding and reduced strain tolerance. | Species/environment boundary conditions, transport path and kinetics, reaction-product growth, evolving interface properties, and exposure time. |
| High-temperature dwell + evolving residual stress -> creep/relaxation and competing crack paths | Failure may shift between oxidation-assisted unbridged crack growth, fibre degradation, creep-driven flaw growth, and internal attack; a single temperature-independent cohesive law cannot distinguish these regimes. | Time-, temperature-, and environment-dependent creep/damage law; initial residual stress; coupled exposure/load history; failure-mode-resolved outputs. |

NASA's SiC/SiC studies supply the direct basis for these chains.  A thermal
gradient rig was built to superimpose through-thickness temperature gradients
and static/dynamic loading while examining creep and fatigue.  Separate EBC
work reports significant in-plane thermal residual stresses from thermal and
elastic mismatch, with coating thickness and modulus affecting the result.
NASA also reports that elevated-temperature SiC/SiC failure can change between
oxidation-induced unbridged cracking and fibre degradation/creep-related
processes as stress and exposure conditions change.  These are coupled
mechanisms, not five independent scalar penalties.

## Consequences for the fracture quantity

The repository already rightly treats the bridged fixed-crack domain integral
as a diagnostic rather than a path-independent material toughness.  Thermal
coupling strengthens that boundary.  A conventional elastic \(J\)-integral does
not by itself account for evolving cohesive damage, frictional contact,
creep, chemical reaction, or changing temperature fields.  A future model
must therefore declare the energy balance and fracture-driving output for its
chosen constitutive framework, and demonstrate numerical convergence under
the coupled field solution.  Reporting one scalar `j_integral_proxy` across
all thermal histories would conceal the mode transition the analysis is meant
to resolve.

## A bounded next modelling slice

The smallest honest extension is **one-way thermoelastic coupling on the
existing fixed geometry**:

1. solve a stated conduction problem for \(T(x)\) with declared boundary
   conditions and temperature-dependent phase properties;
2. initialise a separately declared residual-stress state (or state that it is
   omitted);
3. apply \(\varepsilon_{th}\) in the mechanical solve alongside the existing
   traction; and
4. report temperature-field convergence, mechanical-field convergence, and
   the existing non-path-independent fracture diagnostic separately.

This slice must not claim oxidation, coating spallation, fibre degradation,
creep, interface debonding, or a calibrated CMC response.  Each requires at
least one additional evolving state and independent evidence.  It does,
however, make the word “thermal” mean a reproducible field calculation rather
than a dashboard input.

## Primary sources

- Kalluri, S., Bhatt, R. T., and Phillips, R. E. (2020). *Experimental Setup
  and Parameters for Testing Uncoated and EBC-Coated CMCs Under Thermal
  Gradients Induced by Laser Heating and Backside Air Cooling*,
  NASA/CR-20205004439. [NASA NTRS record](https://ntrs.nasa.gov/citations/20205004439).
  It documents a controlled thermal-gradient test configuration.
- NASA NTRS record [20090013863](https://ntrs.nasa.gov/citations/20090013863).
  Primary source for EBC/CMC mismatch-generated residual stresses and the
  influence of coating stiffness and thickness.
- NASA NTRS record [20080006464](https://ntrs.nasa.gov/citations/20080006464).
  Primary source for stress- and exposure-dependent competing elevated-
  temperature SiC/SiC damage modes.
- NASA NTRS record [20250006556](https://ntrs.nasa.gov/citations/20250006556).
  Primary source for combustion-environment ingress, bond-coat oxidation,
  delamination/spallation, and exposed-CMC recession.
- NASA NTRS record [19920040480](https://ntrs.nasa.gov/citations/19920040480).
  Primary source for matrix cracking, fibre/matrix debonding, thermal effects,
  and their energy balance.
- Morscher, G. N. (1997). *Single-Tow Minicomposite Test Used to Determine the
  Stressed-Oxidation Durability of SiC/SiC Composites*. [NASA NTRS record
  20050177919](https://ntrs.nasa.gov/citations/20050177919).  Establishes why
  oxidation of the interphase changes interface-mediated failure rather than
  merely reducing a bulk strength value.

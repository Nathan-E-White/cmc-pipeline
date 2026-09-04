# Research note: authority for V2 reversible bridging parameters

## Decision addressed

Can published primary evidence justify numerical values of initial stiffness
\(K\), peak traction \(t_p\), and zero-traction opening \(\delta_f\) for the
repository's proposed, history-free, reversible, Mode-I effective crack-plane
bridging law?

## Recommendation

**No.  Use a declared synthetic, non-calibrated V2 parameter card.**  I found
high-quality primary CMC observations that are useful for deciding what data a
future calibration would need, but none that identify all three parameters for
this law and this case.  In particular, do not fit an irreversible
interface-decohesion or frictional-bridging result and call the result a
reversible effective-crack-plane law.

The V2 card should be selected only to exercise the four numerical branches
(elastic, peak, softening, zero traction), state its units and derived
\(\delta_p=t_p/K\), and call \(t_p\delta_f/2\) a *recoverable interface-potential
scale*.  It must not call any value a SiC/SiC property, interface strength,
fracture energy, toughness, or experimental calibration.

## What the primary evidence does establish

- NASA Glenn's **melt-infiltrated SiC/SiC** tensile study used SEM, DIC, and
  manual crack-opening measurements to observe matrix-crack evolution under
  uniaxial tension.  It reports that crack openings increased linearly with
  increasing applied stress and that no crack traversed the full gauge
  cross-section in the examined architecture.  This is directly relevant
  evidence that COD, constituent architecture, and loading state matter; it
  is not a measured local traction--opening curve, unloading/reloading test,
  or a \(K,t_p,\delta_f\) identification. [NASA GRC,
  *Crack Opening Displacement Behavior in Ceramic Matrix Composites*
  (2017)](https://ntrs.nasa.gov/citations/20170009567)

- NASA's high-temperature Sylramic-iBN/MI-SiC/SiC campaign reports explicitly
  that stress, time, temperature, and oxidation alter damage and failure
  mechanisms.  That makes its values non-transferable to the present
  room-temperature, fixed-geometry tracer absent the same architecture,
  environment, loading history, and reduction model. [NASA,
  *Tensile Creep and Fatigue of Sylramic-iBN Melt-Infiltrated SiC Matrix
  Composites* (2008)](https://ntrs.nasa.gov/citations/20080006464)

- NASA's original crack-bridging analysis successfully compared measured
  crack-opening profiles with fibre-pressure/shear-lag models, but the system
  was **SCS-6/Ti-15-3 metal-matrix composite** under fatigue, and the model
  concerns fibre bridging and closure pressure.  It is neither a ceramic
  SiC/SiC data source nor a reversible bilinear cohesive calibration.
  [Ghosn, Kantzos, and Telesman,
  *Modeling of crack bridging in a unidirectional metal matrix composite*
  (1992)](https://ntrs.nasa.gov/citations/19920060461)

## Why available cohesive parameters are rejected

NASA's composite decohesion formulation supplies a valuable bilinear
traction--separation *form*, but it has a damage initiation/evolution model
for delamination.  Its strengths and energy parameters belong to that
irreversible interface model; importing them would silently add a different
material system, interface geometry, and irreversible state.  They therefore
cannot calibrate V2's history-free law. [Camanho and Dávila, *Mixed-Mode
Decohesion Finite Elements for the Simulation of Delamination in Composite
Materials*, NASA/TM-2002-211737
(2002)](https://ntrs.nasa.gov/citations/20020078517)

Likewise, physical CMC bridging is generally conditioned by matrix cracking,
interface debonding, relative sliding, intact-fibre bridging, fibre fracture,
and pullout.  A fitted curve from any one of those mechanisms would be
architecture-, temperature-, and history-dependent; making it single-valued
and reversible would be a new modelling assumption, not validation.  NASA's
CMC mechanism overview makes that separation explicit. [NASA, *Toughening
Mechanisms in Ceramic Matrix Composites*
(1988)](https://ntrs.nasa.gov/citations/19880013027)

## Minimum future authority for non-synthetic values

An admissible future parameter source would need, at minimum, a stated
SiC/SiC (or exactly declared alternative) architecture and interface,
temperature/environment, crack geometry, and a reproducible inverse procedure
that measures crack opening and bridging traction or an equivalent specimen
response.  It must also include unloading/reloading data showing that the
chosen reversible law is valid over the stated range.  If the observations
instead show debonding, slip, residual opening, or degradation, they belong to
the deferred irreversible/contact model rather than V2.

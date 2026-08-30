# 0001: Begin V2 with a prescribed fixed-crack bridging tracer

## Status

Accepted

## Context

V1 established mesh and J-convergence evidence for one isotropic edge-crack case. A CMC-specific next step must make a bridging mechanism explicit, without claiming resolved fibre, coating, interface, damage, or calibrated material behaviour.

## Decision

V2 begins with the same opened edge-crack geometry and a linear-elastic plane-strain bulk material. It applies a prescribed, linearly tapered crack-face closure traction from crack mouth to tip. The crack remains fixed.

`reference-solver converge-bridged-case --output <directory>` is the public interface. It emits the same mesh/audit, field, visual, and convergence artifact family as V1. Its domain integral is a numerical diagnostic, not a path-independent toughness measure or an analytical comparison target.

## Consequences

The tracer makes the proposed CMC-relevant mechanism inspectable with a small interface and preserves V1 as an unchanged comparator. It deliberately omits traction-separation coupling, debond/slip, friction, fibre resolution, crack advance, thermal effects, calibration, and all surrogate or deployment work. Those omissions make its claims narrow, which is cheaper than discovering later that a dashboard has acquired a material model by accident.

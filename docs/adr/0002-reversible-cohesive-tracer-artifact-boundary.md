# 0002: Publish reversible-cohesive results as bounded numerical artifacts

## Status

Accepted

## Context

The V2 reversible tracer couples declared paired exterior crack lips through a
synthetic, history-free bilinear normal-opening law under monotonic prescribed
top displacement. It is a numerical tracer, not a measured CMC constitutive
model. A successful coarse run and an explicit medium-level compression stop
demonstrate why public output must preserve individual mesh-level outcomes,
rather than reduce them to one convergence number.

## Decision

`reference-solver converge-reversible-cohesive-case --output <directory>` is
the public interface. It writes `reversible-cohesive-convergence.json`, a
medium-mesh `case-visual.svg`, mesh audits, paired-lip maps, and every
single-step attempt artifact. Each level is reported as `solved`, `failed`, or
`indeterminate`; a failed or indeterminate level prevents refinement comparison
from being represented as available.

Reaction, trapezoidal external work, bulk strain energy, and reversible
interface potential are numerical accounting quantities within the declared
model. Energy closure is reported, not assumed. The domain-integral J values
are diagnostic-only. Neither J nor the reversible interface potential is
fracture energy, toughness, calibration, experimental validation,
qualification, or design authority.

## Consequences

The small public command exposes a complete, inspectable numerical record
without widening into a generic cohesive/contact framework. V1 and the
prescribed-traction V2 case remain unchanged comparators. Compression,
contact, friction, irreversible damage, crack advance, fibre resolution,
thermal coupling, surrogate inference, and measured-material calibration stay
outside this tracer.

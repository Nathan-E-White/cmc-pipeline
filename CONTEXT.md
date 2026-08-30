# CMC Fracture Pipeline

This context describes a workflow that compares a high-fidelity CMC-fracture simulation with a learned acceleration model.  Its terms separate physical outputs, numerical reference evidence, and permissible surrogate use.

## Language

**Reference solution**:
The finite-element result for a declared input, constitutive model, discretization, and solver configuration.  It is a comparison authority within that model, not experimental truth or a qualified structural prediction.
_Avoid_: ground truth, exact solution

**Surrogate**:
A learned approximation to selected reference-solution outputs over a bounded input domain.
_Avoid_: solver replacement, physics engine

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

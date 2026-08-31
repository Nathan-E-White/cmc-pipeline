"""Control a bounded monotonic displacement trace through one solve seam.

``MonotonicDisplacementProgram`` owns progression, rejected attempts, cutbacks,
and the mouth-opening endpoint.  Its caller supplies the one thing that varies
across this seam: an adapter which solves one prescribed top displacement.
Neither a cohesive-law parameter nor a nonlinear method is changed here.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
from typing import Any, Callable, Mapping


class MonotonicProgramError(ValueError):
    """The declared program is not a finite monotonic displacement trace."""


@dataclass(frozen=True)
class SingleDisplacementResult:
    """The deliberately small result required from a one-step solver adapter."""

    solved: bool
    mouth_opening_mm: float | None = None
    newton_iterations: int | None = None
    relative_residual: float | None = None
    residual_history: tuple[float, ...] = ()
    reversible_interface_potential_mpa_mm2: float | None = None
    diagnostics: Mapping[str, Any] = field(default_factory=dict)
    failure: str | None = None


@dataclass(frozen=True)
class MonotonicDisplacementProgram:
    """Deep load-program module behind one ``run`` interface."""

    initial_increment_mm: float
    maximum_displacement_mm: float
    mouth_opening_target_mm: float
    relative_endpoint_tolerance: float
    relative_residual_max: float
    iterations_max: int
    cutback_factor: float
    consecutive_cutbacks_max: int
    normalized_increment_min: float

    @classmethod
    def from_case_card(cls, card: Mapping[str, Any]) -> "MonotonicDisplacementProgram":
        try:
            program = card["loading"]["program"]
            endpoint = program["endpoint"]
            newton = program["newton"]
            return cls(
                initial_increment_mm=float(program["initial_increment_mm"]),
                maximum_displacement_mm=float(program["maximum_displacement_mm"]),
                mouth_opening_target_mm=float(endpoint["mouth_opening_mm"]),
                relative_endpoint_tolerance=float(endpoint["relative_tolerance"]),
                relative_residual_max=float(newton["relative_residual_max"]),
                iterations_max=int(newton["iterations_max"]),
                cutback_factor=float(newton["cutback_factor"]),
                consecutive_cutbacks_max=int(newton["consecutive_cutbacks_max"]),
                normalized_increment_min=float(newton["normalized_increment_min"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise MonotonicProgramError("case card has no complete monotonic displacement program") from error

    def __post_init__(self) -> None:
        positive = (
            self.initial_increment_mm,
            self.maximum_displacement_mm,
            self.mouth_opening_target_mm,
            self.relative_endpoint_tolerance,
            self.relative_residual_max,
            self.normalized_increment_min,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in positive):
            raise MonotonicProgramError("program magnitudes and tolerances must be finite and positive")
        if self.initial_increment_mm > self.maximum_displacement_mm:
            raise MonotonicProgramError("initial increment cannot exceed maximum displacement")
        if not 0.0 < self.cutback_factor < 1.0:
            raise MonotonicProgramError("cutback factor must be strictly between zero and one")
        if self.iterations_max <= 0 or self.consecutive_cutbacks_max <= 0:
            raise MonotonicProgramError("iteration and cutback limits must be positive")

    @property
    def endpoint_tolerance_mm(self) -> float:
        return self.relative_endpoint_tolerance * self.mouth_opening_target_mm

    def _evidence(
        self, *, phase: str, displacement_mm: float, increment_mm: float,
        result: SingleDisplacementResult, accepted: bool, cutbacks: int,
    ) -> dict[str, Any]:
        item = {
            "phase": phase,
            "accepted": accepted,
            "top_displacement_mm": displacement_mm,
            "load_factor": displacement_mm / self.maximum_displacement_mm,
            "increment_mm": increment_mm,
            "normalized_increment": increment_mm / self.maximum_displacement_mm,
            "mouth_opening_mm": result.mouth_opening_mm,
            "newton_iterations": result.newton_iterations,
            "relative_residual": result.relative_residual,
            "residual_history": list(result.residual_history),
            "cutbacks_before_attempt": cutbacks,
            "reversible_interface_potential_mpa_mm2": result.reversible_interface_potential_mpa_mm2,
            "diagnostics": dict(result.diagnostics),
            "reaction": result.diagnostics.get("reaction", {"status": "unavailable"}),
            "external_work": result.diagnostics.get("external_work", {"status": "unavailable"}),
            "bulk_strain_energy": result.diagnostics.get("bulk_strain_energy", {"status": "unavailable"}),
            "j_diagnostic": result.diagnostics.get("j", {"status": "unavailable"}),
        }
        if not accepted:
            item["failure"] = result.failure or "single-step solver did not converge"
        return item

    def _valid_success(self, result: SingleDisplacementResult) -> bool:
        return (
            result.solved
            and result.mouth_opening_mm is not None
            and math.isfinite(result.mouth_opening_mm)
            and result.newton_iterations is not None
            and result.newton_iterations <= self.iterations_max
            and result.relative_residual is not None
            and math.isfinite(result.relative_residual)
            and result.relative_residual <= self.relative_residual_max
        )

    def run(self, solve: Callable[[float], SingleDisplacementResult]) -> dict[str, Any]:
        """Run until the declared mouth event or an explicit kill switch fires."""
        attempts: list[dict[str, Any]] = []
        accepted: list[dict[str, Any]] = []
        current_displacement = 0.0
        current_mouth = 0.0
        increment = self.initial_increment_mm
        consecutive_cutbacks = 0

        def attempt(phase: str, displacement: float, step_increment: float) -> SingleDisplacementResult | None:
            nonlocal consecutive_cutbacks, increment
            result = solve(displacement)
            if self._valid_success(result):
                evidence = self._evidence(phase=phase, displacement_mm=displacement, increment_mm=step_increment,
                                          result=result, accepted=True, cutbacks=consecutive_cutbacks)
                attempts.append(evidence); accepted.append(evidence)
                consecutive_cutbacks = 0
                return result
            attempts.append(self._evidence(phase=phase, displacement_mm=displacement, increment_mm=step_increment,
                                           result=result, accepted=False, cutbacks=consecutive_cutbacks))
            consecutive_cutbacks += 1
            increment *= self.cutback_factor
            return None

        while current_displacement < self.maximum_displacement_mm:
            proposed = min(current_displacement + increment, self.maximum_displacement_mm)
            result = attempt("advance", proposed, proposed - current_displacement)
            if result is None:
                if (consecutive_cutbacks >= self.consecutive_cutbacks_max or
                        increment / self.maximum_displacement_mm < self.normalized_increment_min):
                    return self._artifact("failed", attempts, accepted, "nonlinear cutback kill switch", consecutive_cutbacks)
                continue
            mouth = result.mouth_opening_mm
            assert mouth is not None
            if abs(mouth - self.mouth_opening_target_mm) <= self.endpoint_tolerance_mm:
                return self._artifact("solved", attempts, accepted, None, consecutive_cutbacks)
            if current_mouth < self.mouth_opening_target_mm < mouth:
                return self._bisect(solve, attempts, accepted, current_displacement, current_mouth, proposed, mouth)
            current_displacement, current_mouth = proposed, mouth
            increment = self.initial_increment_mm
        return self._artifact("indeterminate", attempts, accepted, "maximum displacement reached before mouth-opening event", consecutive_cutbacks)

    def _bisect(self, solve, attempts, accepted, low_displacement, low_mouth, high_displacement, high_mouth) -> dict[str, Any]:
        del low_mouth, high_mouth
        for _ in range(80):
            middle = (low_displacement + high_displacement) / 2.0
            result = solve(middle)
            increment = min(middle - low_displacement, high_displacement - middle)
            if not self._valid_success(result):
                attempts.append(self._evidence(phase="endpoint-bisection", displacement_mm=middle, increment_mm=increment,
                                                result=result, accepted=False, cutbacks=0))
                return self._artifact("failed", attempts, accepted, "endpoint bisection solve failed", 0)
            evidence = self._evidence(phase="endpoint-bisection", displacement_mm=middle, increment_mm=increment,
                                      result=result, accepted=True, cutbacks=0)
            attempts.append(evidence); accepted.append(evidence)
            mouth = result.mouth_opening_mm
            assert mouth is not None
            if abs(mouth - self.mouth_opening_target_mm) <= self.endpoint_tolerance_mm:
                return self._artifact("solved", attempts, accepted, None, 0)
            if mouth < self.mouth_opening_target_mm:
                low_displacement = middle
            else:
                high_displacement = middle
        return self._artifact("indeterminate", attempts, accepted, "endpoint bisection iteration limit", 0)

    def _artifact(self, status, attempts, accepted, failure, cutbacks) -> dict[str, Any]:
        return {
            "status": status,
            "failure": failure,
            "program": asdict(self),
            "endpoint": {"quantity": "mouth-opening", "target_mm": self.mouth_opening_target_mm,
                         "tolerance_mm": self.endpoint_tolerance_mm},
            "attempts": attempts,
            "accepted_increments": accepted,
            "consecutive_cutbacks_at_exit": cutbacks,
        }

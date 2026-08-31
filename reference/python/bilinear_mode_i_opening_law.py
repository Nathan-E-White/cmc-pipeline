"""History-free, reversible bilinear Mode-I traction--opening law.

This module deliberately knows only its scalar law parameters and a
non-negative normal opening.  Mesh pairing, quadrature, case cards, and
nonlinear-solver policy belong to later modules.
"""

from __future__ import annotations

from dataclasses import dataclass
import math


class OpeningLawError(ValueError):
    """The law configuration or queried opening is outside this model's scope."""


@dataclass(frozen=True)
class OpeningLawResponse:
    """Traction, branch tangent, and recoverable potential at one opening."""

    traction_mpa: float
    tangent_mpa_per_mm: float
    reversible_potential_mpa_mm: float


@dataclass(frozen=True)
class BilinearModeIOpeningLaw:
    """A continuous bilinear tensile law with no state or unloading history.

    The tangent returned at the peak opening is the elastic-side tangent, as
    specified by the first branch.  At and beyond final opening it is zero,
    as specified by the final branch.  These choices make the branch rule
    explicit at the two nondifferentiable points.
    """

    peak_traction_mpa: float
    peak_opening_mm: float
    final_opening_mm: float

    def __post_init__(self) -> None:
        for name, value in (
            ("peak_traction_mpa", self.peak_traction_mpa),
            ("peak_opening_mm", self.peak_opening_mm),
            ("final_opening_mm", self.final_opening_mm),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise OpeningLawError(f"{name} must be a finite numeric value")
            if value <= 0.0:
                raise OpeningLawError(f"{name} must be positive")
        if self.peak_opening_mm >= self.final_opening_mm:
            raise OpeningLawError("peak_opening_mm must be less than final_opening_mm")

    @property
    def initial_tangent_mpa_per_mm(self) -> float:
        """The elastic branch tangent implied by the two peak parameters."""
        return self.peak_traction_mpa / self.peak_opening_mm

    @property
    def softening_tangent_mpa_per_mm(self) -> float:
        """The constant tangent on the descending branch."""
        return -self.peak_traction_mpa / (self.final_opening_mm - self.peak_opening_mm)

    @property
    def final_reversible_potential_mpa_mm(self) -> float:
        """The bounded stored potential once traction has fallen to zero."""
        return 0.5 * self.peak_traction_mpa * self.final_opening_mm

    def evaluate(self, opening_mm: float) -> OpeningLawResponse:
        """Evaluate the law at a non-negative normal opening in millimetres."""
        if isinstance(opening_mm, bool) or not isinstance(opening_mm, (int, float)) or not math.isfinite(opening_mm):
            raise OpeningLawError("opening_mm must be a finite numeric value")
        if opening_mm < 0.0:
            raise OpeningLawError("opening_mm must be non-negative; compression is out of scope")

        opening = float(opening_mm)
        if opening <= self.peak_opening_mm:
            traction = self.initial_tangent_mpa_per_mm * opening
            return OpeningLawResponse(
                traction_mpa=traction,
                tangent_mpa_per_mm=self.initial_tangent_mpa_per_mm,
                reversible_potential_mpa_mm=0.5 * traction * opening,
            )
        if opening < self.final_opening_mm:
            traction = self.peak_traction_mpa * (self.final_opening_mm - opening) / (
                self.final_opening_mm - self.peak_opening_mm
            )
            potential_at_peak = 0.5 * self.peak_traction_mpa * self.peak_opening_mm
            potential_after_peak = 0.5 * (self.peak_traction_mpa + traction) * (
                opening - self.peak_opening_mm
            )
            return OpeningLawResponse(
                traction_mpa=traction,
                tangent_mpa_per_mm=self.softening_tangent_mpa_per_mm,
                reversible_potential_mpa_mm=potential_at_peak + potential_after_peak,
            )
        return OpeningLawResponse(
            traction_mpa=0.0,
            tangent_mpa_per_mm=0.0,
            reversible_potential_mpa_mm=self.final_reversible_potential_mpa_mm,
        )

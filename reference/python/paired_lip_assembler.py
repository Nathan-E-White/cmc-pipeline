"""Assemble a reversible normal-opening law on declared paired crack lips.

``PairedLipAssembler`` is deliberately the only module that knows how a
quadratic pair is interpolated and integrated.  It consumes the generator's
declared pair map; it neither discovers facets nor derives a pairing from
coordinates or physical groups.  PETSc/DOLFINx ownership and load-program
policy remain outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Protocol, Sequence

from bilinear_mode_i_opening_law import OpeningLawError, OpeningLawResponse


class PairedLipAssemblyError(ValueError):
    """A declared pair or its displacement field is outside this tracer."""


class NormalOpeningLaw(Protocol):
    """Internal seam for a history-free response to a non-negative opening."""

    peak_opening_mm: float
    final_opening_mm: float

    def evaluate(self, opening_mm: float) -> OpeningLawResponse: ...


@dataclass(frozen=True)
class PairedLipContribution:
    """Nodal residual and consistent tangent for one or more declared pairs."""

    residual_by_node: dict[int, tuple[float, float]]
    tangent_by_node_pair: dict[tuple[int, int], tuple[tuple[float, float], tuple[float, float]]]
    reversible_potential_mpa_mm2: float
    quadrature_subintervals: int


def _zero_matrix() -> list[list[float]]:
    return [[0.0, 0.0], [0.0, 0.0]]


def _add_matrix(target: list[list[float]], source: Sequence[Sequence[float]], scale: float = 1.0) -> None:
    for row in range(2):
        for column in range(2):
            target[row][column] += scale * source[row][column]


class PairedLipAssembler:
    """Deep implementation of paired-lip quadrature behind one assembly call.

    Its interface takes the public pair-map document and a node-id keyed
    displacement field.  The returned residual is the internal-force
    contribution: plus receives ``+t n`` and minus receives ``-t n``.  Thus
    every quadrature point is equal and opposite, and the tangent is the
    derivative of the declared reversible potential.
    """

    _GAUSS_POINTS = (-math.sqrt(3.0 / 5.0), 0.0, math.sqrt(3.0 / 5.0))
    _GAUSS_WEIGHTS = (5.0 / 9.0, 8.0 / 9.0, 5.0 / 9.0)

    def __init__(self, law: NormalOpeningLaw, normal_minus_to_plus: Sequence[float]) -> None:
        if len(normal_minus_to_plus) != 2:
            raise PairedLipAssemblyError("normal_minus_to_plus must have two entries")
        normal = tuple(float(value) for value in normal_minus_to_plus)
        magnitude = math.hypot(*normal)
        if not math.isfinite(magnitude) or not math.isclose(magnitude, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise PairedLipAssemblyError("normal_minus_to_plus must be a finite unit vector")
        self._law = law
        self._normal = normal

    @classmethod
    def from_pair_map(cls, law: NormalOpeningLaw, pair_map: Mapping[str, Any]) -> "PairedLipAssembler":
        """Construct from the map's declared normal, without inferring one."""
        try:
            normal = pair_map["reference_trace"]["normal_minus_to_plus"]
        except (KeyError, TypeError) as error:
            raise PairedLipAssemblyError("pair map has no declared minus-to-plus normal") from error
        return cls(law, normal)

    @staticmethod
    def _lip_nodes(pair: Mapping[str, Any], side: str) -> tuple[list[int], list[float]]:
        try:
            lip = pair[side]
            nodes = list(lip["node_ids"])
            coordinates = [float(value) for value in lip["reference_coordinates_mm"]]
        except (KeyError, TypeError, ValueError) as error:
            raise PairedLipAssemblyError(f"declared {side} lip is malformed") from error
        if len(nodes) != 3 or len(coordinates) != 3 or len(set(nodes)) != 3:
            raise PairedLipAssemblyError(f"declared {side} lip must contain three distinct quadratic nodes")
        if any(not isinstance(node, int) or node <= 0 for node in nodes):
            raise PairedLipAssemblyError(f"declared {side} lip has invalid node identifiers")
        return nodes, coordinates

    @staticmethod
    def _reference_interval(pair: Mapping[str, Any]) -> tuple[float, float]:
        try:
            start, end = (float(value) for value in pair["reference_interval_mm"])
        except (KeyError, TypeError, ValueError) as error:
            raise PairedLipAssemblyError("pair has no valid reference interval") from error
        if not math.isfinite(start) or not math.isfinite(end) or end <= start:
            raise PairedLipAssemblyError("pair reference interval must increase")
        return start, end

    @staticmethod
    def _shape_values(s_mm: float, coordinates_mm: Sequence[float], start_mm: float, end_mm: float) -> list[float]:
        """Evaluate generic quadratic Lagrange values in declared node order."""
        xi = 2.0 * (s_mm - start_mm) / (end_mm - start_mm) - 1.0
        xis = [2.0 * (coordinate - start_mm) / (end_mm - start_mm) - 1.0 for coordinate in coordinates_mm]
        if len(set(round(value, 14) for value in xis)) != 3:
            raise PairedLipAssemblyError("quadratic lip reference coordinates must be distinct")
        values: list[float] = []
        for index, xi_i in enumerate(xis):
            value = 1.0
            for other_index, xi_j in enumerate(xis):
                if index != other_index:
                    value *= (xi - xi_j) / (xi_i - xi_j)
            values.append(value)
        return values

    @staticmethod
    def _normal_displacements(nodes: Sequence[int], values: Mapping[int, Sequence[float]], normal: tuple[float, float]) -> list[float]:
        openings: list[float] = []
        for node in nodes:
            try:
                displacement = values[node]
                x, y = float(displacement[0]), float(displacement[1])
            except (KeyError, IndexError, TypeError, ValueError) as error:
                raise PairedLipAssemblyError(f"no finite two-dimensional displacement for node {node}") from error
            if not math.isfinite(x) or not math.isfinite(y):
                raise PairedLipAssemblyError(f"no finite two-dimensional displacement for node {node}")
            openings.append(x * normal[0] + y * normal[1])
        return openings

    def _breakpoints(self, pair: Mapping[str, Any], nodal_opening: Sequence[float], coordinates: Sequence[float]) -> list[float]:
        start, end = self._reference_interval(pair)
        # Recover q(xi)=a xi^2+b xi+c from the declared quadratic interpolation.
        at_minus = sum(weight * value for weight, value in zip(self._shape_values(start, coordinates, start, end), nodal_opening, strict=True))
        at_zero = sum(weight * value for weight, value in zip(self._shape_values((start + end) / 2.0, coordinates, start, end), nodal_opening, strict=True))
        at_plus = sum(weight * value for weight, value in zip(self._shape_values(end, coordinates, start, end), nodal_opening, strict=True))
        a = (at_plus + at_minus - 2.0 * at_zero) / 2.0
        b = (at_plus - at_minus) / 2.0
        c = at_zero

        roots: list[float] = []
        for threshold in (self._law.peak_opening_mm, self._law.final_opening_mm):
            if math.isclose(a, 0.0, rel_tol=0.0, abs_tol=1e-14):
                candidates = [] if math.isclose(b, 0.0, rel_tol=0.0, abs_tol=1e-14) else [(threshold - c) / b]
            else:
                discriminant = b * b - 4.0 * a * (c - threshold)
                if discriminant < -1e-14:
                    candidates = []
                else:
                    root = math.sqrt(max(discriminant, 0.0))
                    candidates = [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]
            roots.extend(candidate for candidate in candidates if -1.0 + 1e-12 < candidate < 1.0 - 1e-12)
        return [-1.0, *sorted({round(root, 14) for root in roots}), 1.0]

    @staticmethod
    def _quadratic_coefficients(
        pair: Mapping[str, Any], nodal_values: Sequence[float], coordinates: Sequence[float]
    ) -> tuple[float, float, float]:
        """Return q(xi)=a xi^2+b xi+c for declared quadratic values."""
        start, end = PairedLipAssembler._reference_interval(pair)
        at_minus = sum(weight * value for weight, value in zip(
            PairedLipAssembler._shape_values(start, coordinates, start, end), nodal_values, strict=True
        ))
        at_zero = sum(weight * value for weight, value in zip(
            PairedLipAssembler._shape_values((start + end) / 2.0, coordinates, start, end), nodal_values, strict=True
        ))
        at_plus = sum(weight * value for weight, value in zip(
            PairedLipAssembler._shape_values(end, coordinates, start, end), nodal_values, strict=True
        ))
        return (
            (at_plus + at_minus - 2.0 * at_zero) / 2.0,
            (at_plus - at_minus) / 2.0,
            at_zero,
        )

    @staticmethod
    def _minimum_quadratic(a: float, b: float, c: float) -> float:
        """Minimize a quadratic on the closed reference interval [-1, 1]."""
        candidates = [-1.0, 1.0]
        if a > 0.0:
            stationary = -b / (2.0 * a)
            if -1.0 < stationary < 1.0:
                candidates.append(stationary)
        return min(a * xi * xi + b * xi + c for xi in candidates)

    def _pair_nodal_opening(
        self, pair: Mapping[str, Any], displacements_by_node: Mapping[int, Sequence[float]]
    ) -> tuple[list[float], list[float]]:
        """Evaluate the declared plus-minus opening at the P2 nodal coordinates."""
        start, end = self._reference_interval(pair)
        minus_nodes, minus_coordinates = self._lip_nodes(pair, "minus")
        plus_nodes, plus_coordinates = self._lip_nodes(pair, "plus")
        if sorted(minus_coordinates) != sorted(plus_coordinates):
            raise PairedLipAssemblyError("paired lips must share their declared reference coordinates")
        minus_normal = self._normal_displacements(minus_nodes, displacements_by_node, self._normal)
        plus_normal = self._normal_displacements(plus_nodes, displacements_by_node, self._normal)
        return [
            sum(self._shape_values(s, plus_coordinates, start, end)[index] * plus_normal[index] for index in range(3)) -
            sum(self._shape_values(s, minus_coordinates, start, end)[index] * minus_normal[index] for index in range(3))
            for s in plus_coordinates
        ], plus_coordinates

    def maximum_feasible_step(
        self,
        pair_map: Mapping[str, Any],
        displacements_by_node: Mapping[int, Sequence[float]],
        increment_by_node: Mapping[int, Sequence[float]],
    ) -> float:
        """Return the largest safe scale in [0, 1] for a proposed displacement increment.

        The minimum is evaluated analytically for every declared quadratic lip,
        so a line-search trial cannot hide compression between quadrature points.
        A bisection supplies a strict interior scale when the full update is not
        feasible.  It is solver policy to decide what a zero scale means.
        """
        try:
            pairs = pair_map["ordered_element_pairs"]
        except (KeyError, TypeError) as error:
            raise PairedLipAssemblyError("pair map has no ordered element pairs") from error
        if not isinstance(pairs, list) or not pairs:
            raise PairedLipAssemblyError("pair map must declare at least one element pair")

        def feasible(scale: float) -> bool:
            candidate = {
                node: (
                    float(displacements_by_node[node][0]) + scale * float(increment_by_node[node][0]),
                    float(displacements_by_node[node][1]) + scale * float(increment_by_node[node][1]),
                )
                for node in displacements_by_node
            }
            return self.minimum_opening(pair_map, candidate) >= 0.0

        if not feasible(0.0):
            raise PairedLipAssemblyError("current declared paired-lip state is in compression")
        if feasible(1.0):
            return 1.0
        lower, upper = 0.0, 1.0
        for _ in range(80):
            middle = (lower + upper) / 2.0
            if feasible(middle):
                lower = middle
            else:
                upper = middle
        return math.nextafter(lower, 0.0)

    def minimum_opening(self, pair_map: Mapping[str, Any], displacements_by_node: Mapping[int, Sequence[float]]) -> float:
        """Return the exact minimum normal opening across all declared P2 lips."""
        try:
            pairs = pair_map["ordered_element_pairs"]
        except (KeyError, TypeError) as error:
            raise PairedLipAssemblyError("pair map has no ordered element pairs") from error
        if not isinstance(pairs, list) or not pairs:
            raise PairedLipAssemblyError("pair map must declare at least one element pair")
        minimum = math.inf
        for pair in pairs:
            values, coordinates = self._pair_nodal_opening(pair, displacements_by_node)
            minimum = min(minimum, self._minimum_quadratic(*self._quadratic_coefficients(pair, values, coordinates)))
        return minimum

    def assemble(self, pair_map: Mapping[str, Any], displacements_by_node: Mapping[int, Sequence[float]]) -> PairedLipContribution:
        """Integrate every declared pair with kink-aligned three-point Gauss rules."""
        try:
            pairs = pair_map["ordered_element_pairs"]
        except (KeyError, TypeError) as error:
            raise PairedLipAssemblyError("pair map has no ordered element pairs") from error
        if not isinstance(pairs, list) or not pairs:
            raise PairedLipAssemblyError("pair map must declare at least one element pair")

        residual: dict[int, list[float]] = {}
        tangent: dict[tuple[int, int], list[list[float]]] = {}
        potential = 0.0
        subintervals = 0
        outer_normal = ((self._normal[0] * self._normal[0], self._normal[0] * self._normal[1]),
                        (self._normal[1] * self._normal[0], self._normal[1] * self._normal[1]))

        for pair in pairs:
            start, end = self._reference_interval(pair)
            minus_nodes, minus_coordinates = self._lip_nodes(pair, "minus")
            plus_nodes, plus_coordinates = self._lip_nodes(pair, "plus")
            if sorted(minus_coordinates) != sorted(plus_coordinates):
                raise PairedLipAssemblyError("paired lips must share their declared reference coordinates")
            minus_normal = self._normal_displacements(minus_nodes, displacements_by_node, self._normal)
            plus_normal = self._normal_displacements(plus_nodes, displacements_by_node, self._normal)
            # Both lips are interpolated at the common reference coordinate; no facet discovery occurs here.
            nodal_opening = [
                sum(self._shape_values(s, plus_coordinates, start, end)[index] * plus_normal[index] for index in range(3)) -
                sum(self._shape_values(s, minus_coordinates, start, end)[index] * minus_normal[index] for index in range(3))
                for s in (start, end, (start + end) / 2.0)
            ]
            breakpoints = self._breakpoints(pair, nodal_opening, plus_coordinates)
            for left, right in zip(breakpoints, breakpoints[1:]):
                subintervals += 1
                for gauss_point, gauss_weight in zip(self._GAUSS_POINTS, self._GAUSS_WEIGHTS, strict=True):
                    xi = (left + right) / 2.0 + (right - left) * gauss_point / 2.0
                    s_mm = start + (xi + 1.0) * (end - start) / 2.0
                    minus_shape = self._shape_values(s_mm, minus_coordinates, start, end)
                    plus_shape = self._shape_values(s_mm, plus_coordinates, start, end)
                    opening = sum(shape * value for shape, value in zip(plus_shape, plus_normal, strict=True)) - sum(shape * value for shape, value in zip(minus_shape, minus_normal, strict=True))
                    try:
                        response = self._law.evaluate(opening)
                    except OpeningLawError as error:
                        raise PairedLipAssemblyError(f"negative opening at declared pair quadrature point: {opening}") from error
                    factor = gauss_weight * (right - left) * (end - start) / 4.0
                    potential += factor * response.reversible_potential_mpa_mm
                    sides = ((minus_nodes, minus_shape, -1.0), (plus_nodes, plus_shape, 1.0))
                    for nodes_i, shapes_i, sign_i in sides:
                        for node_i, shape_i in zip(nodes_i, shapes_i, strict=True):
                            vector = residual.setdefault(node_i, [0.0, 0.0])
                            vector[0] += sign_i * factor * shape_i * response.traction_mpa * self._normal[0]
                            vector[1] += sign_i * factor * shape_i * response.traction_mpa * self._normal[1]
                            for nodes_j, shapes_j, sign_j in sides:
                                for node_j, shape_j in zip(nodes_j, shapes_j, strict=True):
                                    matrix = tangent.setdefault((node_i, node_j), _zero_matrix())
                                    _add_matrix(matrix, outer_normal, factor * shape_i * shape_j * sign_i * sign_j * response.tangent_mpa_per_mm)
        return PairedLipContribution(
            residual_by_node={node: (value[0], value[1]) for node, value in residual.items()},
            tangent_by_node_pair={key: ((value[0][0], value[0][1]), (value[1][0], value[1][1])) for key, value in tangent.items()},
            reversible_potential_mpa_mm2=potential,
            quadrature_subintervals=subintervals,
        )

"""Generate and validate the paired artifacts for the fixed opened edge crack.

This module deliberately knows one declared straight trace.  It records the
pairing while the Gmsh Crack plugin's duplicated topology is observable, then
translates node identifiers through the explicit export renumbering map.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "opened-crack-face-pairs/v1"
TRACE_ID = "edge-cracked-plate-v1:crack_trace"
TRACE_LENGTH_MM = 30.0
TRACE_Y_MM = 100.0
TOLERANCE_MM = 1e-8


class OpenedCrackArtifactError(ValueError):
    """An exported mesh and its declared paired-lip contract disagree."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_digest(value: Any) -> str:
    return _sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def _require(mapping: dict[str, Any], *keys: str) -> None:
    missing = [key for key in keys if key not in mapping]
    if missing:
        raise OpenedCrackArtifactError(f"missing required field(s): {', '.join(missing)}")


def _as_vector(value: Any, name: str, length: int) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise OpenedCrackArtifactError(f"{name} must contain {length} values")
    if any(isinstance(entry, bool) or not isinstance(entry, (int, float)) for entry in value):
        raise OpenedCrackArtifactError(f"{name} must be numeric")
    return [float(entry) for entry in value]


def validate_pair_map_document(payload: Any, mesh_digest: str) -> None:
    """Validate the JSON contract before opening the mesh with Gmsh."""
    if not isinstance(payload, dict):
        raise OpenedCrackArtifactError("pair map must be an object")
    _require(
        payload,
        "schema_version",
        "mesh_digest",
        "pairing_digest",
        "reference_trace",
        "tip_policy",
        "quadrature",
        "ordered_element_pairs",
    )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise OpenedCrackArtifactError("unsupported schema version")
    digest = payload["mesh_digest"]
    if not isinstance(digest, dict) or digest.get("algorithm") != "sha256":
        raise OpenedCrackArtifactError("mesh digest must declare sha256")
    if digest.get("value") != mesh_digest:
        raise OpenedCrackArtifactError("mesh digest does not match the exported mesh")

    trace = payload["reference_trace"]
    if not isinstance(trace, dict):
        raise OpenedCrackArtifactError("reference trace must be an object")
    _require(trace, "id", "units", "direction", "length_mm", "tolerance_mm", "tangent", "normal_minus_to_plus")
    if trace["id"] != TRACE_ID or trace["units"] != "mm" or trace["direction"] != "mouth-to-tip":
        raise OpenedCrackArtifactError("unexpected reference trace declaration")
    if not math.isclose(float(trace["length_mm"]), TRACE_LENGTH_MM, rel_tol=0.0, abs_tol=TOLERANCE_MM):
        raise OpenedCrackArtifactError("unexpected reference trace length")
    if not math.isclose(float(trace["tolerance_mm"]), TOLERANCE_MM, rel_tol=0.0, abs_tol=1e-15):
        raise OpenedCrackArtifactError("unexpected reference tolerance")
    tangent = _as_vector(trace["tangent"], "reference tangent", 2)
    normal = _as_vector(trace["normal_minus_to_plus"], "reference normal", 2)
    if tangent != [1.0, 0.0] or normal != [0.0, 1.0]:
        raise OpenedCrackArtifactError("unexpected minus-to-plus frame")

    tip_policy = payload["tip_policy"]
    if not isinstance(tip_policy, dict) or tip_policy.get("kind") != "sealed-shared-tip-excluded-from-quadrature-endpoints":
        raise OpenedCrackArtifactError("unexpected sealed-tip policy")
    if not math.isclose(float(tip_policy.get("reference_s_mm", math.nan)), TRACE_LENGTH_MM, rel_tol=0.0, abs_tol=TOLERANCE_MM):
        raise OpenedCrackArtifactError("sealed tip must be at the reference-trace endpoint")
    quadrature = payload["quadrature"]
    if quadrature != {"family": "gauss-legendre", "points_per_smooth_subinterval": 3, "measure": "reference"}:
        raise OpenedCrackArtifactError("unexpected quadrature convention")

    pairs = payload["ordered_element_pairs"]
    if not isinstance(pairs, list) or not pairs:
        raise OpenedCrackArtifactError("ordered element pairs must be a non-empty list")
    digest_record = payload["pairing_digest"]
    if not isinstance(digest_record, dict) or digest_record.get("algorithm") != "sha256":
        raise OpenedCrackArtifactError("pairing digest must declare sha256")
    if digest_record.get("value") != _canonical_digest(pairs):
        raise OpenedCrackArtifactError("pairing digest does not match ordered element pairs")

    seen_elements: set[int] = set()
    paired_non_tip_nodes: dict[int, int] = {}
    paired_non_tip_nodes_reverse: dict[int, int] = {}
    expected_start = 0.0
    for index, pair in enumerate(pairs):
        if not isinstance(pair, dict):
            raise OpenedCrackArtifactError(f"pair {index} must be an object")
        _require(pair, "reference_interval_mm", "minus", "plus", "reference_node_correspondences")
        interval = _as_vector(pair["reference_interval_mm"], f"pair {index} reference interval", 2)
        if not math.isclose(interval[0], expected_start, rel_tol=0.0, abs_tol=TOLERANCE_MM) or interval[1] <= interval[0]:
            raise OpenedCrackArtifactError(f"pair {index} does not continue the canonical reference ordering")
        expected_start = interval[1]
        lips: dict[str, dict[str, Any]] = {}
        for name in ("minus", "plus"):
            lip = pair[name]
            if not isinstance(lip, dict):
                raise OpenedCrackArtifactError(f"pair {index} {name} lip must be an object")
            _require(lip, "element_id", "node_ids", "reference_coordinates_mm", "local_coordinate_at_reference_start_end")
            element_id = lip["element_id"]
            if isinstance(element_id, bool) or not isinstance(element_id, int) or element_id <= 0 or element_id in seen_elements:
                raise OpenedCrackArtifactError(f"pair {index} has duplicate or invalid {name} element")
            seen_elements.add(element_id)
            node_ids = lip["node_ids"]
            if not isinstance(node_ids, list) or len(node_ids) != 3 or len(set(node_ids)) != 3 or any(not isinstance(node, int) or node <= 0 for node in node_ids):
                raise OpenedCrackArtifactError(f"pair {index} {name} lip must contain one quadratic element")
            coordinates = _as_vector(lip["reference_coordinates_mm"], f"pair {index} {name} reference coordinates", 3)
            expected_coordinates = [interval[0], (interval[0] + interval[1]) / 2.0, interval[1]]
            if any(
                not math.isclose(actual, expected, rel_tol=0.0, abs_tol=TOLERANCE_MM)
                for actual, expected in zip(sorted(coordinates), expected_coordinates, strict=True)
            ):
                raise OpenedCrackArtifactError(f"pair {index} {name} nodes do not match the declared interval")
            local_coordinates = _as_vector(lip["local_coordinate_at_reference_start_end"], f"pair {index} {name} local coordinate mapping", 2)
            if sorted(local_coordinates) != [-1.0, 1.0]:
                raise OpenedCrackArtifactError(f"pair {index} {name} local coordinate map is invalid")
            lips[name] = lip
        correspondences = pair["reference_node_correspondences"]
        if not isinstance(correspondences, list) or len(correspondences) != 3:
            raise OpenedCrackArtifactError(f"pair {index} must declare all quadratic-node correspondences")
        by_reference: dict[float, dict[str, Any]] = {}
        for correspondence in correspondences:
            if not isinstance(correspondence, dict):
                raise OpenedCrackArtifactError(f"pair {index} correspondence must be an object")
            _require(correspondence, "reference_s_mm", "minus_node_id", "plus_node_id")
            s = float(correspondence["reference_s_mm"])
            by_reference[s] = correspondence
            if correspondence["minus_node_id"] not in lips["minus"]["node_ids"] or correspondence["plus_node_id"] not in lips["plus"]["node_ids"]:
                raise OpenedCrackArtifactError(f"pair {index} correspondence refers to a foreign node")
            for name, node_key in (("minus", "minus_node_id"), ("plus", "plus_node_id")):
                node_index = lips[name]["node_ids"].index(correspondence[node_key])
                node_coordinate = lips[name]["reference_coordinates_mm"][node_index]
                if not math.isclose(s, node_coordinate, rel_tol=0.0, abs_tol=TOLERANCE_MM):
                    raise OpenedCrackArtifactError(f"pair {index} correspondence has the wrong reference coordinate")
            if math.isclose(s, TRACE_LENGTH_MM, rel_tol=0.0, abs_tol=TOLERANCE_MM):
                if correspondence["minus_node_id"] != correspondence["plus_node_id"]:
                    raise OpenedCrackArtifactError("sealed tip must use the shared endpoint node")
            else:
                if correspondence["minus_node_id"] == correspondence["plus_node_id"]:
                    raise OpenedCrackArtifactError("non-tip crack-lip nodes must be distinct")
                minus_node = correspondence["minus_node_id"]
                plus_node = correspondence["plus_node_id"]
                if paired_non_tip_nodes.get(minus_node, plus_node) != plus_node or paired_non_tip_nodes_reverse.get(plus_node, minus_node) != minus_node:
                    raise OpenedCrackArtifactError("non-tip nodes must have one consistent correspondence")
                paired_non_tip_nodes[minus_node] = plus_node
                paired_non_tip_nodes_reverse[plus_node] = minus_node
        expected_coordinates = [interval[0], (interval[0] + interval[1]) / 2.0, interval[1]]
        if len(by_reference) != 3 or any(
            not any(math.isclose(actual, expected, rel_tol=0.0, abs_tol=TOLERANCE_MM) for actual in by_reference)
            for expected in expected_coordinates
        ):
            raise OpenedCrackArtifactError(f"pair {index} correspondence coordinates do not match the quadratic nodes")
    if not math.isclose(expected_start, TRACE_LENGTH_MM, rel_tol=0.0, abs_tol=TOLERANCE_MM):
        raise OpenedCrackArtifactError("pair map does not cover the declared trace")


def _node_coordinates(gmsh: Any) -> dict[int, tuple[float, float]]:
    tags, coordinates, _ = gmsh.model.mesh.getNodes()
    return {int(tag): (float(coordinates[index * 3]), float(coordinates[index * 3 + 1])) for index, tag in enumerate(tags)}


def _physical_entities(gmsh: Any, name: str) -> list[int]:
    matches = [tag for dimension, tag in gmsh.model.getPhysicalGroups(1) if gmsh.model.getPhysicalName(dimension, tag) == name]
    if len(matches) != 1:
        raise OpenedCrackArtifactError(f"expected one physical group named {name}")
    entities = [int(entity) for entity in gmsh.model.getEntitiesForPhysicalGroup(1, matches[0])]
    if len(entities) != 1:
        raise OpenedCrackArtifactError(f"expected one trace entity in physical group {name}")
    return entities


def _quadratic_line_elements(gmsh: Any, entity: int) -> list[tuple[int, list[int]]]:
    element_types, element_tags, element_nodes = gmsh.model.mesh.getElements(1, entity)
    result: list[tuple[int, list[int]]] = []
    for element_type, tags, nodes in zip(element_types, element_tags, element_nodes, strict=True):
        name, dimension, order, node_count, _, _ = gmsh.model.mesh.getElementProperties(int(element_type))
        if dimension != 1:
            continue
        if order != 2 or node_count != 3:
            raise OpenedCrackArtifactError(f"{name} is not a quadratic line element")
        for offset, tag in enumerate(tags):
            result.append((int(tag), [int(node) for node in nodes[offset * node_count : (offset + 1) * node_count]]))
    if not result:
        raise OpenedCrackArtifactError("crack trace has no quadratic line elements")
    return result


def _facet_side_by_element(gmsh: Any, coordinates: dict[int, tuple[float, float]]) -> dict[frozenset[int], str]:
    edge_sides: dict[frozenset[int], list[str]] = {}
    element_types, _, element_nodes = gmsh.model.mesh.getElements(2)
    for element_type, nodes in zip(element_types, element_nodes, strict=True):
        _, dimension, order, node_count, _, primary_nodes = gmsh.model.mesh.getElementProperties(int(element_type))
        if dimension != 2 or order != 2 or primary_nodes != 3:
            continue
        for offset in range(0, len(nodes), node_count):
            corners = [int(node) for node in nodes[offset : offset + primary_nodes]]
            centroid_y = sum(coordinates[node][1] for node in corners) / 3.0
            if math.isclose(centroid_y, TRACE_Y_MM, rel_tol=0.0, abs_tol=TOLERANCE_MM):
                continue
            side = "minus" if centroid_y < TRACE_Y_MM else "plus"
            for start, end in ((0, 1), (1, 2), (2, 0)):
                edge_sides.setdefault(frozenset((corners[start], corners[end])), []).append(side)
    resolved: dict[frozenset[int], str] = {}
    for edge, sides in edge_sides.items():
        if len(sides) == 1:
            resolved[edge] = sides[0]
    return resolved


def _capture_pair_map_before_renumbering(gmsh: Any) -> dict[str, Any]:
    coordinates = _node_coordinates(gmsh)
    original_entity = _physical_entities(gmsh, "crack_trace")[0]
    created_entity = _physical_entities(gmsh, "crack_faces")[0]
    side_by_edge = _facet_side_by_element(gmsh, coordinates)
    traces: dict[str, list[dict[str, Any]]] = {"minus": [], "plus": []}
    for entity in (original_entity, created_entity):
        for element_id, node_ids in _quadratic_line_elements(gmsh, entity):
            endpoints = frozenset((node_ids[0], node_ids[1]))
            side = side_by_edge.get(endpoints)
            if side is None:
                raise OpenedCrackArtifactError("crack-face element is not an exterior facet of exactly one bulk cell")
            values = [coordinates[node][0] for node in node_ids]
            if any(not math.isclose(coordinates[node][1], TRACE_Y_MM, rel_tol=0.0, abs_tol=TOLERANCE_MM) for node in node_ids):
                raise OpenedCrackArtifactError("crack-face node is outside the declared straight reference trace")
            interval = (min(values[0], values[1]), max(values[0], values[1]))
            traces[side].append(
                {
                    "element_id": element_id,
                    "node_ids": node_ids,
                    "reference_coordinates_mm": values,
                    "interval": interval,
                    "local_coordinate_at_reference_start_end": [
                        -1.0 if math.isclose(values[0], interval[0], rel_tol=0.0, abs_tol=TOLERANCE_MM) else 1.0,
                        -1.0 if math.isclose(values[1], interval[0], rel_tol=0.0, abs_tol=TOLERANCE_MM) else 1.0,
                    ],
                }
            )
    if not traces["minus"] or not traces["plus"]:
        raise OpenedCrackArtifactError("opened mesh must expose one minus and one plus lip")
    for side in traces:
        traces[side].sort(key=lambda entry: entry["interval"])
    if len(traces["minus"]) != len(traces["plus"]):
        raise OpenedCrackArtifactError("opened lips have unequal element counts")

    pairs: list[dict[str, Any]] = []
    for minus, plus in zip(traces["minus"], traces["plus"], strict=True):
        if minus["interval"] != plus["interval"]:
            raise OpenedCrackArtifactError("opened lips have different reference-arclength partitions")
        interval = minus["interval"]
        def node_at(lip: dict[str, Any], s: float) -> int:
            matches = [node for node, coordinate in zip(lip["node_ids"], lip["reference_coordinates_mm"], strict=True) if math.isclose(coordinate, s, rel_tol=0.0, abs_tol=TOLERANCE_MM)]
            if len(matches) != 1:
                raise OpenedCrackArtifactError("quadratic lip has no unique node at a reference coordinate")
            return matches[0]
        correspondences = [
            {"reference_s_mm": s, "minus_node_id": node_at(minus, s), "plus_node_id": node_at(plus, s)}
            for s in (interval[0], (interval[0] + interval[1]) / 2.0, interval[1])
        ]
        pairs.append(
            {
                "reference_interval_mm": list(interval),
                "minus": {key: minus[key] for key in ("element_id", "node_ids", "reference_coordinates_mm", "local_coordinate_at_reference_start_end")},
                "plus": {key: plus[key] for key in ("element_id", "node_ids", "reference_coordinates_mm", "local_coordinate_at_reference_start_end")},
                "reference_node_correspondences": correspondences,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "reference_trace": {
            "id": TRACE_ID,
            "units": "mm",
            "direction": "mouth-to-tip",
            "length_mm": TRACE_LENGTH_MM,
            "tolerance_mm": TOLERANCE_MM,
            "tangent": [1.0, 0.0],
            "normal_minus_to_plus": [0.0, 1.0],
        },
        "tip_policy": {
            "kind": "sealed-shared-tip-excluded-from-quadrature-endpoints",
            "reference_s_mm": TRACE_LENGTH_MM,
        },
        "quadrature": {"family": "gauss-legendre", "points_per_smooth_subinterval": 3, "measure": "reference"},
        "ordered_element_pairs": pairs,
    }


def _translate_node_ids(payload: dict[str, Any], node_mapping: dict[int, int]) -> None:
    for pair in payload["ordered_element_pairs"]:
        for lip in (pair["minus"], pair["plus"]):
            lip["node_ids"] = [node_mapping[node] for node in lip["node_ids"]]
        for correspondence in pair["reference_node_correspondences"]:
            correspondence["minus_node_id"] = node_mapping[correspondence["minus_node_id"]]
            correspondence["plus_node_id"] = node_mapping[correspondence["plus_node_id"]]


def generate_opened_crack_mesh(
    case: Path,
    output: Path,
    near_size: float,
    far_size: float,
    pairs_output: Path | None,
) -> None:
    """Generate the existing mesh and optionally its audited pairing artifact."""
    import gmsh

    gmsh.initialize()
    try:
        gmsh.open(str(case))
        gmsh.option.setNumber("Mesh.MeshSizeMin", near_size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", far_size)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.setOrder(2)
        gmsh.plugin.setNumber("Crack", "Dimension", 1)
        gmsh.plugin.setNumber("Crack", "PhysicalGroup", 4)
        gmsh.plugin.setNumber("Crack", "OpenBoundaryPhysicalGroup", 6)
        gmsh.plugin.setNumber("Crack", "NormalZ", 1)
        gmsh.plugin.setNumber("Crack", "NewPhysicalGroup", 7)
        gmsh.plugin.run("Crack")
        payload = _capture_pair_map_before_renumbering(gmsh) if pairs_output is not None else None
        if payload is None:
            gmsh.model.mesh.renumberNodes()
        else:
            old_tags, _, _ = gmsh.model.mesh.getNodes()
            new_tags = list(range(1, len(old_tags) + 1))
            node_mapping = {int(old): new for old, new in zip(old_tags, new_tags, strict=True)}
            gmsh.model.mesh.renumberNodes([int(tag) for tag in old_tags], new_tags)
            _translate_node_ids(payload, node_mapping)
        gmsh.write(str(output))
        if payload is not None:
            payload["mesh_digest"] = {"algorithm": "sha256", "value": _sha256_bytes(output.read_bytes())}
            payload["pairing_digest"] = {"algorithm": "sha256", "value": _canonical_digest(payload["ordered_element_pairs"])}
            pairs_output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    finally:
        gmsh.finalize()
    if pairs_output is not None:
        validate_exported_artifacts(output, pairs_output)


def validate_exported_artifacts(mesh_path: Path, pairs_path: Path) -> None:
    """Validate the pair document and then its identifiers/topology against Gmsh."""
    payload = json.loads(pairs_path.read_text(encoding="utf-8"))
    validate_pair_map_document(payload, _sha256_bytes(mesh_path.read_bytes()))
    import gmsh

    gmsh.initialize()
    try:
        gmsh.open(str(mesh_path))
        coordinates = _node_coordinates(gmsh)
        original_entity = _physical_entities(gmsh, "crack_trace")[0]
        created_entity = _physical_entities(gmsh, "crack_faces")[0]
        side_by_edge = _facet_side_by_element(gmsh, coordinates)
        actual: dict[int, tuple[str, list[int]]] = {}
        for entity in (original_entity, created_entity):
            for element_id, node_ids in _quadratic_line_elements(gmsh, entity):
                side = side_by_edge.get(frozenset((node_ids[0], node_ids[1])))
                if side is None:
                    raise OpenedCrackArtifactError("exported crack-face element is not an exterior facet of exactly one bulk cell")
                actual[element_id] = (side, node_ids)
        declared_ids: set[int] = set()
        for pair in payload["ordered_element_pairs"]:
            for name in ("minus", "plus"):
                lip = pair[name]
                element_id = lip["element_id"]
                declared_ids.add(element_id)
                if element_id not in actual or actual[element_id][0] != name or actual[element_id][1] != lip["node_ids"]:
                    raise OpenedCrackArtifactError("pair map element identifiers do not match the exported crack traces")
                for node, s in zip(lip["node_ids"], lip["reference_coordinates_mm"], strict=True):
                    x, y = coordinates[node]
                    if not math.isclose(x, s, rel_tol=0.0, abs_tol=TOLERANCE_MM) or not math.isclose(y, TRACE_Y_MM, rel_tol=0.0, abs_tol=TOLERANCE_MM):
                        raise OpenedCrackArtifactError("pair map reference-node coordinate does not match the exported mesh")
        if declared_ids != set(actual):
            raise OpenedCrackArtifactError("pair map does not bijectively cover the exported crack-face elements")
    finally:
        gmsh.finalize()

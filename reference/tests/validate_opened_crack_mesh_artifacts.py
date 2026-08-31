#!/usr/bin/env python3
"""Contract tests for the generator-owned opened-crack mesh artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "reference/python/validate_opened_crack_mesh_artifacts.py"


def _pair_map(mesh_digest: str, *, shared_non_tip_node: bool = False) -> dict:
    plus_nodes = [11, 2, 13]
    if shared_non_tip_node:
        plus_nodes[0] = 1
    payload = {
        "schema_version": "opened-crack-face-pairs/v1",
        "mesh_digest": {"algorithm": "sha256", "value": mesh_digest},
        "reference_trace": {
            "id": "edge-cracked-plate-v1:crack_trace",
            "units": "mm",
            "direction": "mouth-to-tip",
            "length_mm": 30.0,
            "tolerance_mm": 1e-8,
            "tangent": [1.0, 0.0],
            "normal_minus_to_plus": [0.0, 1.0],
        },
        "tip_policy": {
            "kind": "sealed-shared-tip-excluded-from-quadrature-endpoints",
            "reference_s_mm": 30.0,
        },
        "quadrature": {
            "family": "gauss-legendre",
            "points_per_smooth_subinterval": 3,
            "measure": "reference",
        },
        "ordered_element_pairs": [
            {
                "reference_interval_mm": [0.0, 30.0],
                "minus": {
                    "element_id": 101,
                    "node_ids": [1, 2, 3],
                    "reference_coordinates_mm": [0.0, 30.0, 15.0],
                    "local_coordinate_at_reference_start_end": [-1.0, 1.0],
                },
                "plus": {
                    "element_id": 201,
                    "node_ids": plus_nodes,
                    "reference_coordinates_mm": [0.0, 30.0, 15.0],
                    "local_coordinate_at_reference_start_end": [-1.0, 1.0],
                },
                "reference_node_correspondences": [
                    {"reference_s_mm": 0.0, "minus_node_id": 1, "plus_node_id": plus_nodes[0]},
                    {"reference_s_mm": 15.0, "minus_node_id": 3, "plus_node_id": plus_nodes[2]},
                    {"reference_s_mm": 30.0, "minus_node_id": 2, "plus_node_id": plus_nodes[1]},
                ],
            }
        ],
    }
    payload["pairing_digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(
            json.dumps(payload["ordered_element_pairs"], sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest(),
    }
    return payload


def _validate(mesh_bytes: bytes, payload: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        mesh = root / "mesh.msh"
        pairs = root / "crack-face-pairs.json"
        mesh.write_bytes(mesh_bytes)
        pairs.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--mesh", str(mesh), "--pairs", str(pairs)],
            text=True,
            capture_output=True,
            check=False,
        )


def test_validator_rejects_a_stale_mesh_digest_before_reading_the_mesh() -> None:
    result = _validate(b"not a gmsh mesh", _pair_map("0" * 64))
    assert result.returncode != 0
    assert "mesh digest" in result.stderr


def test_validator_rejects_a_shared_non_tip_node_before_reading_the_mesh() -> None:
    mesh_bytes = b"not a gmsh mesh"
    result = _validate(
        mesh_bytes,
        _pair_map(hashlib.sha256(mesh_bytes).hexdigest(), shared_non_tip_node=True),
    )
    assert result.returncode != 0
    assert "non-tip" in result.stderr


if __name__ == "__main__":
    test_validator_rejects_a_stale_mesh_digest_before_reading_the_mesh()
    test_validator_rejects_a_shared_non_tip_node_before_reading_the_mesh()

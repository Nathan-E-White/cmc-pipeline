#!/usr/bin/env python3
"""Generate the V1 mesh and use Gmsh's Crack plugin to open the crack lips."""

from __future__ import annotations

import argparse
from pathlib import Path

from opened_crack_mesh_artifacts import generate_opened_crack_mesh


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--near-size", type=float, required=True)
    parser.add_argument("--far-size", type=float, required=True)
    parser.add_argument("--crack-face-pairs-output", type=Path)
    args = parser.parse_args()
    generate_opened_crack_mesh(
        args.case,
        args.output,
        args.near_size,
        args.far_size,
        args.crack_face_pairs_output,
    )


if __name__ == "__main__":
    main()

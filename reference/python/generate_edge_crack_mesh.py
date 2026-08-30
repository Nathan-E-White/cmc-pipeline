#!/usr/bin/env python3
"""Generate the V1 mesh and use Gmsh's Crack plugin to open the crack lips."""

from __future__ import annotations

import argparse
from pathlib import Path

import gmsh


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--near-size", type=float, required=True)
    parser.add_argument("--far-size", type=float, required=True)
    args = parser.parse_args()

    gmsh.initialize()
    try:
        gmsh.open(str(args.case))
        gmsh.option.setNumber("Mesh.MeshSizeMin", args.near_size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", args.far_size)
        gmsh.model.mesh.generate(2)
        gmsh.model.mesh.setOrder(2)
        gmsh.plugin.setNumber("Crack", "Dimension", 1)
        gmsh.plugin.setNumber("Crack", "PhysicalGroup", 4)
        gmsh.plugin.setNumber("Crack", "OpenBoundaryPhysicalGroup", 6)
        gmsh.plugin.setNumber("Crack", "NormalZ", 1)
        gmsh.plugin.setNumber("Crack", "NewPhysicalGroup", 7)
        gmsh.plugin.run("Crack")
        # DOLFINx requires the node identifiers in a Gmsh file to be a dense
        # sequence.  The Crack plugin duplicates nodes but does not preserve
        # that property, so normalize the exported mesh after opening the lips.
        gmsh.model.mesh.renumberNodes()
        gmsh.write(str(args.output))
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()

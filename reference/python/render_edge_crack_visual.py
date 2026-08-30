#!/usr/bin/env python3
"""Render a deterministic SVG directly from the generated benchmark mesh."""
from __future__ import annotations

import argparse
from pathlib import Path

import gmsh


def point(x: float, y: float) -> tuple[float, float]:
    return (60 + x * 5, 1040 - y * 5)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gmsh.initialize()
    try:
        gmsh.open(str(args.mesh))
        tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = {tag: (coordinates[index], coordinates[index + 1]) for index, tag in enumerate(tags) for index in (index * 3,)}
        element_types, _, element_nodes = gmsh.model.mesh.getElements(2)
        triangles = next(nodes_for_type for kind, nodes_for_type in zip(element_types, element_nodes) if kind == 9)
        polygons = []
        for index in range(0, len(triangles), 6):
            vertices = [point(*nodes[tag]) for tag in triangles[index:index + 3]]
            polygons.append("<path d=\"M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in vertices) + " Z\"/>")
        args.output.write_text("""<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 650 1120\">
<rect width=\"650\" height=\"1120\" fill=\"#f8f5ed\"/><style>text{font-family:Arial,sans-serif;fill:#151515} .mesh{fill:none;stroke:#426b8a;stroke-width:.45} .bc{stroke:#b43d2d;stroke-width:4} .support{stroke:#151515;stroke-width:4}</style>
<text x=\"60\" y=\"45\" font-size=\"22\">EDGE-CRACKED PLATE V1</text><text x=\"60\" y=\"70\" font-size=\"13\">actual medium generated quadratic mesh and declared boundary conditions</text>
<g class=\"mesh\">""" + "".join(polygons) + """</g>
<line class=\"bc\" x1=\"560\" y1=\"40\" x2=\"560\" y2=\"1040\"/><text x=\"570\" y=\"95\" font-size=\"14\">loaded: 100 MPa</text>
<line class=\"support\" x1=\"60\" y1=\"1040\" x2=\"560\" y2=\"1040\"/><text x=\"65\" y=\"1080\" font-size=\"14\">support_y; x anchor at origin</text>
<line x1=\"60\" y1=\"540\" x2=\"210\" y2=\"540\" stroke=\"#b43d2d\" stroke-width=\"5\"/><circle cx=\"210\" cy=\"540\" r=\"7\" fill=\"#b43d2d\"/><text x=\"220\" y=\"530\" font-size=\"14\">opened crack faces; tip</text>
</svg>""", encoding="utf-8")
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render a deterministic SVG directly from the generated benchmark mesh."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import gmsh

MARGIN = 60
SCALE = 5
BOTTOM = 1040
CANVAS_WIDTH = 650
CANVAS_HEIGHT = 1120


def mesh_to_svg(x: float, y: float) -> tuple[float, float]:
    return (MARGIN + x * SCALE, BOTTOM - y * SCALE)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-card", type=Path, required=True)
    args = parser.parse_args()
    gmsh.initialize()
    try:
        gmsh.open(str(args.mesh))
        tags, coordinates, _ = gmsh.model.mesh.getNodes()
        nodes = {tag: (coordinates[index], coordinates[index + 1]) for index, tag in enumerate(tags) for index in (index * 3,)}
        element_types, _, element_nodes = gmsh.model.mesh.getElements(2)
        triangles = next(nodes_for_type for kind, nodes_for_type in zip(element_types, element_nodes) if kind == 9)
        card = json.loads(args.case_card.read_text(encoding="utf-8"))
        polygons = []
        for index in range(0, len(triangles), 6):
            vertices = [mesh_to_svg(*nodes[tag]) for tag in triangles[index:index + 3]]
            polygons.append("<path d=\"M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in vertices) + " Z\"/>")
        def boundary_path(name: str) -> str:
            for dimension, tag in gmsh.model.getPhysicalGroups(1):
                if gmsh.model.getPhysicalName(dimension, tag) != name:
                    continue
                group_points = []
                for entity in gmsh.model.getEntitiesForPhysicalGroup(dimension, tag):
                    _, coordinates, _ = gmsh.model.mesh.getNodes(dimension, entity, includeBoundary=True)
                    group_points.extend((coordinates[index], coordinates[index + 1]) for index in range(0, len(coordinates), 3))
                return " ".join(
                    f"{x:.2f},{y:.2f}" for x, y in (mesh_to_svg(*xy) for xy in sorted(set(group_points)))
                )
            raise RuntimeError(f"Missing physical boundary: {name}")

        loaded, support, crack = (boundary_path(name) for name in ("loaded", "support_y", "crack_faces"))
        title = card["case_id"].replace("-", " ").upper()
        loading_label = ""
        model_label = ""
        if "bridging" in card["model"]:
            bridging = card["model"]["bridging"]
            loading_label = f"loaded: {card['model']['nominal_traction_mpa']} MPa"
            model_label = (
                f'<text x="220" y="555" font-size="14">prescribed closure traction: '
                f'{bridging["peak_traction_mpa"]} MPa at mouth to 0 MPa at tip</text>'
            )
        elif "cohesive_interface" in card["model"]:
            law = card["model"]["cohesive_interface"]["law"]
            loading_label = "loaded: monotonic prescribed displacement"
            model_label = (
                '<text x="180" y="530" font-size="14">declared paired exterior lips; synthetic reversible normal-opening law</text>'
                f'<text x="205" y="555" font-size="14">peak: {law["peak_traction_mpa"]} MPa at '
                f'{law["peak_opening_mm"]} mm; zero traction at {law["final_opening_mm"]} mm</text>'
            )
        else:
            loading_label = f"loaded: {card['model']['nominal_traction_mpa']} MPa"
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CANVAS_WIDTH} {CANVAS_HEIGHT}">
<rect width=\"{CANVAS_WIDTH}\" height=\"{CANVAS_HEIGHT}\" fill=\"#f8f5ed\"/><style>text{{font-family:Arial,sans-serif;fill:#151515}} .mesh{{fill:none;stroke:#426b8a;stroke-width:.45}} .bc{{stroke:#b43d2d;stroke-width:4}} .support{{stroke:#151515;stroke-width:4}}</style>
<text x=\"{MARGIN}\" y=\"45\" font-size=\"22\">{title}</text><text x=\"{MARGIN}\" y=\"70\" font-size=\"13\">actual medium generated quadratic mesh and declared boundary conditions</text>
<g class="mesh">{"".join(polygons)}</g>
<polyline class=\"bc\" points=\"{loaded}\"/><text x=\"430\" y=\"95\" font-size=\"14\">{loading_label}</text>
<polyline class=\"support\" points=\"{support}\"/><text x=\"65\" y=\"1080\" font-size=\"14\">support_y; x anchor at origin</text>
<polyline points=\"{crack}\" stroke=\"#b43d2d\" stroke-width=\"5\" fill=\"none\"/><text x=\"220\" y=\"505\" font-size=\"14\">opened crack faces</text>{model_label}
</svg>"""
        args.output.write_text(svg, encoding="utf-8")
    finally:
        gmsh.finalize()


if __name__ == "__main__":
    main()

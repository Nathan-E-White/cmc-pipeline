#!/usr/bin/env python3
"""Solve the fixed V1 edge-crack benchmark under plane strain.

This script is deliberately case-specific.  It is the numerical reference
path for the declared benchmark, not a CMC material model or a design tool.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import ufl
from mpi4py import MPI
from petsc4py import PETSc

from dolfinx import fem, io, mesh
from dolfinx.fem.petsc import LinearProblem


E_MPA = 200_000.0
POISSONS_RATIO = 0.3
TRACTION_MPA = 100.0
CRACK_TIP_MM = (30.0, 100.0)


def _write_json(path: Path, payload: dict) -> None:
    if MPI.COMM_WORLD.rank == 0:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _domain_integral_j(domain: mesh.Mesh, displacement: fem.Function, radius_mm: float) -> float:
    """Evaluate the x-directed J quantity with a compact radial weight field."""
    Q = fem.functionspace(domain, ("Lagrange", 1))
    weight = fem.Function(Q)
    tip_x, tip_y = CRACK_TIP_MM

    def radial_weight(points: np.ndarray) -> np.ndarray:
        distance = np.sqrt((points[0] - tip_x) ** 2 + (points[1] - tip_y) ** 2)
        return np.maximum(0.0, 1.0 - distance / radius_mm)

    weight.interpolate(radial_weight)
    identity = ufl.Identity(domain.geometry.dim)
    strain = lambda w: ufl.sym(ufl.grad(w))
    mu = E_MPA / (2.0 * (1.0 + POISSONS_RATIO))
    lame_lambda = E_MPA * POISSONS_RATIO / (
        (1.0 + POISSONS_RATIO) * (1.0 - 2.0 * POISSONS_RATIO)
    )
    stress = lame_lambda * ufl.tr(strain(displacement)) * identity + 2.0 * mu * strain(displacement)
    energy_density = 0.5 * ufl.inner(stress, strain(displacement))
    displacement_x_derivative = ufl.grad(displacement)[:, 0]
    energy_momentum = ufl.dot(stress, displacement_x_derivative) - ufl.as_vector(
        (energy_density, 0.0)
    )
    value = fem.assemble_scalar(fem.form(ufl.dot(energy_momentum, ufl.grad(weight)) * ufl.dx))
    return float(domain.comm.allreduce(value, op=MPI.SUM))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case-card", type=Path, required=True)
    args = parser.parse_args()
    case_card = json.loads(args.case_card.read_text(encoding="utf-8"))
    contours = case_card["fracture_quantity"]["contour_radii_mm"]

    comm = MPI.COMM_WORLD
    mesh_data = io.gmsh.read_from_msh(args.mesh, comm, rank=0, gdim=2)
    domain = mesh_data.mesh
    facet_tags = mesh_data.facet_tags
    if facet_tags is None:
        raise RuntimeError("The benchmark mesh has no facet physical groups.")

    physical_groups = mesh_data.physical_groups
    for name in ("loaded", "support_y", "x_anchor", "crack_faces"):
        if name not in physical_groups:
            raise RuntimeError(f"Missing required physical group: {name}")

    vector_element = ("Lagrange", 2, (domain.geometry.dim,))
    V = fem.functionspace(domain, vector_element)
    u = ufl.TrialFunction(V)
    v = ufl.TestFunction(V)
    identity = ufl.Identity(domain.geometry.dim)
    strain = lambda w: ufl.sym(ufl.grad(w))
    mu = E_MPA / (2.0 * (1.0 + POISSONS_RATIO))
    lame_lambda = E_MPA * POISSONS_RATIO / (
        (1.0 + POISSONS_RATIO) * (1.0 - 2.0 * POISSONS_RATIO)
    )
    stress = lambda w: lame_lambda * ufl.tr(strain(w)) * identity + 2.0 * mu * strain(w)

    dx = ufl.Measure("dx", domain=domain)
    ds = ufl.Measure("ds", domain=domain, subdomain_data=facet_tags)
    a_form = ufl.inner(stress(u), strain(v)) * dx
    traction = fem.Constant(domain, np.array((0.0, TRACTION_MPA), dtype=PETSc.ScalarType))
    l_form = ufl.dot(traction, v) * ds(physical_groups["loaded"].tag)

    support_facets = facet_tags.find(physical_groups["support_y"].tag)
    y_dofs = fem.locate_dofs_topological(V.sub(1), domain.topology.dim - 1, support_facets)
    zero = fem.Constant(domain, PETSc.ScalarType(0))
    bc_y = fem.dirichletbc(zero, y_dofs, V.sub(1))

    anchor_vertices = mesh.locate_entities_boundary(
        domain,
        0,
        lambda x: np.isclose(x[0], 0.0) & np.isclose(x[1], 0.0),
    )
    if len(anchor_vertices) != 1:
        raise RuntimeError(f"Expected one x-anchor vertex, found {len(anchor_vertices)}")
    x_dofs = fem.locate_dofs_topological(V.sub(0), 0, anchor_vertices)
    bc_x = fem.dirichletbc(zero, x_dofs, V.sub(0))

    problem = LinearProblem(
        a_form,
        l_form,
        bcs=[bc_y, bc_x],
        petsc_options_prefix="edge_crack_",
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"},
    )
    displacement = problem.solve()
    displacement.name = "displacement_mm"

    contour_values = [
        {"radius_mm": radius, "j_mpa_mm": _domain_integral_j(domain, displacement, radius)}
        for radius in contours
    ]

    args.output.mkdir(parents=True, exist_ok=True)
    with io.XDMFFile(comm, args.output / "displacement.xdmf", "w") as xdmf:
        xdmf.write_mesh(domain)
        xdmf.write_function(displacement)

    local_values = displacement.x.array
    summary = {
        "case_id": "edge-cracked-plate-v1",
        "status": "solved",
        "model": "linear-elastic plane strain",
        "fixed_external_values": {
            "youngs_modulus_mpa": E_MPA,
            "poissons_ratio": POISSONS_RATIO,
            "nominal_traction_mpa": TRACTION_MPA,
        },
        "displacement_mm": {
            "local_linf": float(np.max(np.abs(local_values))) if local_values.size else 0.0,
        },
        "fracture_quantity": {
            "method": "domain-integral",
            "direction": "crack-extension-x",
            "contours": contour_values,
        },
        "claim_boundary": "One fixed isotropic plane-strain numerical reference solve with a numerical domain-integral fracture quantity; no CMC calibration, physical validation, qualification, or design authority.",
    }
    _write_json(args.output / "solution-summary.json", summary)


if __name__ == "__main__":
    main()

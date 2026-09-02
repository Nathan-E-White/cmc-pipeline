#!/usr/bin/env python3
"""Solve the fixed V1 edge-crack benchmark under plane strain.

This script is deliberately case-specific.  It is the numerical reference
path for the declared benchmark, not a CMC material model or a design tool.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import ufl
from dolfinx import fem, io, mesh
from dolfinx.fem.petsc import LinearProblem
from mpi4py import MPI
from petsc4py import PETSc

CRACK_TIP_MM = (30.0, 100.0)


def _write_json(path: Path, payload: dict) -> None:
    if MPI.COMM_WORLD.rank == 0:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _stress(domain: mesh.Mesh, displacement, youngs_modulus_mpa: float, poissons_ratio: float):
    identity = ufl.Identity(domain.geometry.dim)
    strain = ufl.sym(ufl.grad(displacement))
    mu = youngs_modulus_mpa / (2.0 * (1.0 + poissons_ratio))
    lame_lambda = youngs_modulus_mpa * poissons_ratio / (
        (1.0 + poissons_ratio) * (1.0 - 2.0 * poissons_ratio)
    )
    return lame_lambda * ufl.tr(strain) * identity + 2.0 * mu * strain


def _domain_integral_j(
    domain: mesh.Mesh,
    displacement: fem.Function,
    radius_mm: float,
    youngs_modulus_mpa: float,
    poissons_ratio: float,
) -> float:
    """Evaluate the x-directed J quantity with a compact radial weight field."""
    Q = fem.functionspace(domain, ("Lagrange", 1))
    weight = fem.Function(Q)
    tip_x, tip_y = CRACK_TIP_MM

    def radial_weight(points: np.ndarray) -> np.ndarray:
        distance = np.sqrt((points[0] - tip_x) ** 2 + (points[1] - tip_y) ** 2)
        return np.maximum(0.0, 1.0 - distance / radius_mm)

    weight.interpolate(radial_weight)
    strain = lambda w: ufl.sym(ufl.grad(w))
    stress = _stress(domain, displacement, youngs_modulus_mpa, poissons_ratio)
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
    model = case_card["model"]
    youngs_modulus_mpa = model["youngs_modulus_gpa"] * 1_000.0
    poissons_ratio = model["poissons_ratio"]
    loading = case_card.get("loading")
    nominal_traction_mpa = model.get("nominal_traction_mpa")
    if loading is None and nominal_traction_mpa is None:
        raise RuntimeError("Case card must declare traction or displacement loading.")

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
    strain = lambda w: ufl.sym(ufl.grad(w))
    stress = lambda w: _stress(domain, w, youngs_modulus_mpa, poissons_ratio)

    dx = ufl.Measure("dx", domain=domain)
    ds = ufl.Measure("ds", domain=domain, subdomain_data=facet_tags)
    a_form = ufl.inner(stress(u), strain(v)) * dx
    zero_load = fem.Constant(domain, np.array((0.0, 0.0), dtype=PETSc.ScalarType))
    l_form = ufl.dot(zero_load, v) * dx
    bridging = model.get("bridging")
    if bridging is not None:
        if bridging["kind"] != "prescribed-crack-face-closure-traction":
            raise RuntimeError(f"Unsupported bridging kind: {bridging['kind']}")
        crack_length_mm = case_card["geometry"]["crack_length_mm"]
        coordinates = ufl.SpatialCoordinate(domain)
        closure_mpa = bridging["peak_traction_mpa"] * (1.0 - coordinates[0] / crack_length_mm)
        l_form += ufl.dot(closure_mpa * ufl.FacetNormal(domain), v) * ds(
            physical_groups["crack_faces"].tag
        )

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

    bcs = [bc_y, bc_x]
    if loading is None:
        traction = fem.Constant(domain, np.array((0.0, nominal_traction_mpa), dtype=PETSc.ScalarType))
        l_form += ufl.dot(traction, v) * ds(physical_groups["loaded"].tag)
    elif loading.get("kind") == "prescribed-top-displacement":
        loaded_facets = facet_tags.find(physical_groups["loaded"].tag)
        loaded_dofs = fem.locate_dofs_topological(V.sub(1), domain.topology.dim - 1, loaded_facets)
        displacement_value = fem.Constant(domain, PETSc.ScalarType(loading["top_displacement_mm"]))
        bcs.append(fem.dirichletbc(displacement_value, loaded_dofs, V.sub(1)))
    else:
        raise RuntimeError("Unsupported declared loading kind.")

    problem = LinearProblem(
        a_form,
        l_form,
        bcs=bcs,
        petsc_options_prefix="edge_crack_",
        petsc_options={"ksp_type": "preonly", "pc_type": "lu"},
    )
    displacement = problem.solve()
    displacement.name = "displacement_mm"

    contour_values = [
        {
            "radius_mm": radius,
            "j_mpa_mm": _domain_integral_j(
                domain, displacement, radius, youngs_modulus_mpa, poissons_ratio
            ),
        }
        for radius in contours
    ]

    args.output.mkdir(parents=True, exist_ok=True)
    with io.XDMFFile(comm, args.output / "displacement.xdmf", "w") as xdmf:
        xdmf.write_mesh(domain)
        xdmf.write_function(displacement)

    local_values = displacement.x.array
    summary = {
        "case_id": case_card["case_id"],
        "status": "solved",
        "model": (
            "linear-elastic plane strain with prescribed displacement"
            if loading is not None
            else "linear-elastic plane strain"
            if bridging is None
            else "linear-elastic plane strain with prescribed crack-face closure traction"
        ),
        "fixed_external_values": {
            "youngs_modulus_mpa": youngs_modulus_mpa,
            "poissons_ratio": poissons_ratio,
            **({"nominal_traction_mpa": nominal_traction_mpa} if nominal_traction_mpa is not None else {}),
            **({"loading": loading} if loading is not None else {}),
            **({"bridging": bridging} if bridging is not None else {}),
        },
        "displacement_mm": {
            "local_linf": float(np.max(np.abs(local_values))) if local_values.size else 0.0,
        },
        "fracture_quantity": {
            "method": "domain-integral",
            "direction": "crack-extension-x",
            "contours": contour_values,
        },
        "claim_boundary": case_card["claim_boundary"],
    }
    _write_json(args.output / "solution-summary.json", summary)


if __name__ == "__main__":
    main()

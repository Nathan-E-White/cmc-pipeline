#!/usr/bin/env python3
"""One displacement-controlled PETSc solve for the reversible paired-lip tracer.

This deliberately takes one prescribed top displacement.  Stepping, cutbacks,
and endpoint bisection belong to the later ``MonotonicDisplacementProgram``.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import ufl
from dolfinx import fem, io, mesh
from dolfinx.fem import petsc as fem_petsc
from mpi4py import MPI
from petsc4py import PETSc

from bilinear_mode_i_opening_law import BilinearModeIOpeningLaw
from opened_crack_mesh_artifacts import validate_exported_artifacts
from paired_lip_assembler import PairedLipAssembler
from solve_edge_crack import _domain_integral_j, _stress


def _node_dofs(V, domain, node_ids: set[int]) -> dict[int, tuple[int, int]]:
    """Adapter from exported node IDs to DOLFINx's preserved input identities."""
    block_size = V.dofmap.index_map_bs
    if block_size != 2:
        raise RuntimeError("paired-lip solve requires a two-dimensional blocked displacement space")
    start, end = V.dofmap.index_map.local_range
    identities = domain.geometry.input_global_indices
    by_input_node = {int(node): start + local for local, node in enumerate(identities)}
    result = {
        node: (by_input_node[node] * block_size, by_input_node[node] * block_size + 1)
        for node in node_ids
        if node in by_input_node
    }
    if set(result) != node_ids:
        raise RuntimeError("declared crack-lip nodes are not all present in the imported mesh identity map")
    return result


def _add_contribution(vector, matrix, contribution, node_dofs: dict[int, tuple[int, int]]) -> None:
    """PETSc adapter for the assembler's node-keyed result."""
    if vector is not None:
        for node, value in contribution.residual_by_node.items():
            if node not in node_dofs:
                continue
            vector.setValues(node_dofs[node], value, addv=PETSc.InsertMode.ADD_VALUES)
    if matrix is not None:
        for (row_node, column_node), values in contribution.tangent_by_node_pair.items():
            if row_node not in node_dofs or column_node not in node_dofs:
                continue
            matrix.setValues(node_dofs[row_node], node_dofs[column_node], values, addv=PETSc.InsertMode.ADD_VALUES)


def _mouth_opening_mm(pair_map: dict, displacements: dict[int, tuple[float, float]]) -> float:
    """Read the mouth from the declared map; no coordinate pairing is inferred."""
    correspondence = min(
        pair_map["ordered_element_pairs"][0]["reference_node_correspondences"],
        key=lambda item: float(item["reference_s_mm"]),
    )
    normal = pair_map["reference_trace"]["normal_minus_to_plus"]
    minus = displacements[int(correspondence["minus_node_id"])]
    plus = displacements[int(correspondence["plus_node_id"])]
    return float((plus[0] - minus[0]) * normal[0] + (plus[1] - minus[1]) * normal[1])


def _scalar(domain, expression) -> float:
    """Assemble a real scalar consistently for this single-rank adapter."""
    return float(domain.comm.allreduce(fem.assemble_scalar(fem.form(expression)), op=MPI.SUM))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--crack-face-pairs", type=Path, required=True)
    parser.add_argument("--case-card", type=Path, required=True)
    parser.add_argument("--top-displacement-mm", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.top_displacement_mm < 0.0:
        raise RuntimeError("top displacement must be non-negative for this no-compression tracer")
    validate_exported_artifacts(args.mesh, args.crack_face_pairs)
    pair_map = json.loads(args.crack_face_pairs.read_text(encoding="utf-8"))
    card = json.loads(args.case_card.read_text(encoding="utf-8"))
    law_card = card["model"]["cohesive_interface"]["law"]
    law = BilinearModeIOpeningLaw(law_card["peak_traction_mpa"], law_card["peak_opening_mm"], law_card["final_opening_mm"])
    assembler = PairedLipAssembler.from_pair_map(law, pair_map)

    comm = MPI.COMM_WORLD
    if comm.size != 1:
        raise RuntimeError("the Item 4 paired-lip PETSc adapter currently supports one MPI rank")
    mesh_data = io.gmsh.read_from_msh(args.mesh, comm, rank=0, gdim=2)
    domain, facet_tags, physical_groups = mesh_data.mesh, mesh_data.facet_tags, mesh_data.physical_groups
    if facet_tags is None:
        raise RuntimeError("opened mesh has no physical facet groups")
    for name in ("loaded", "support_y"):
        if name not in physical_groups:
            raise RuntimeError(f"missing physical group {name}")
    V = fem.functionspace(domain, ("Lagrange", 2, (2,)))
    trial, test = ufl.TrialFunction(V), ufl.TestFunction(V)
    youngs = card["model"]["youngs_modulus_gpa"] * 1_000.0
    poisson = card["model"]["poissons_ratio"]
    a = ufl.inner(_stress(domain, trial, youngs, poisson), ufl.sym(ufl.grad(test))) * ufl.dx
    body_force = fem.Constant(domain, np.array((0.0, 0.0), dtype=PETSc.ScalarType))
    L = ufl.inner(body_force, test) * ufl.dx(domain=domain)

    zero = fem.Constant(domain, PETSc.ScalarType(0))
    support_facets = facet_tags.find(physical_groups["support_y"].tag)
    bc_y = fem.dirichletbc(zero, fem.locate_dofs_topological(V.sub(1), domain.topology.dim - 1, support_facets), V.sub(1))
    top = fem.Constant(domain, PETSc.ScalarType(args.top_displacement_mm))
    loaded_facets = facet_tags.find(physical_groups["loaded"].tag)
    bc_top = fem.dirichletbc(top, fem.locate_dofs_topological(V.sub(1), domain.topology.dim - 1, loaded_facets), V.sub(1))
    anchor_vertices = mesh.locate_entities_boundary(domain, 0, lambda x: np.isclose(x[0], 0.0) & np.isclose(x[1], 0.0))
    if len(anchor_vertices) != 1:
        raise RuntimeError("expected exactly one x-anchor")
    bc_x = fem.dirichletbc(zero, fem.locate_dofs_topological(V.sub(0), 0, anchor_vertices), V.sub(0))
    bcs = [bc_y, bc_top, bc_x]

    a_form, l_form = fem.form(a), fem.form(L)
    bulk_matrix = fem_petsc.assemble_matrix(a_form, bcs=bcs)
    bulk_matrix.assemble()
    rhs = fem_petsc.assemble_vector(l_form)
    fem_petsc.apply_lifting(rhs, [a_form], [bcs])
    rhs.ghostUpdate(addv=PETSc.InsertMode.ADD_VALUES, mode=PETSc.ScatterMode.REVERSE)
    fem_petsc.set_bc(rhs, bcs)

    declared_nodes = {
        node
        for pair in pair_map["ordered_element_pairs"]
        for side in ("minus", "plus")
        for node in pair[side]["node_ids"]
    }
    node_dofs = _node_dofs(V, domain, declared_nodes)
    displacement = fem.Function(V)
    # The bulk form cannot preallocate couplings between opposite exterior lips.
    # Reserve enough row entries for both the P2 bulk stencil and all six lip
    # nodes in a declared pair.
    jacobian = PETSc.Mat().createAIJ(size=bulk_matrix.getSize(), nnz=512, comm=comm)
    jacobian.setUp()
    jacobian.assemble()
    jacobian.setOption(PETSc.Mat.Option.NEW_NONZERO_ALLOCATION_ERR, False)
    # Establish the full sparsity pattern once: bulk couplings plus declared
    # opposite-lip couplings.  Subsequent Newton updates only change values.
    jacobian.axpy(1.0, bulk_matrix, structure=PETSc.Mat.Structure.DIFFERENT_NONZERO_PATTERN)
    jacobian.setOption(PETSc.Mat.Option.NEW_NONZERO_ALLOCATION_ERR, False)
    zero_lip_displacements = {node: (0.0, 0.0) for node in declared_nodes}
    _add_contribution(None, jacobian, assembler.assemble(pair_map, zero_lip_displacements), node_dofs)
    jacobian.assemblyBegin(); jacobian.assemblyEnd()
    residual_vector = rhs.duplicate()

    def declared_displacements(x) -> dict[int, tuple[float, float]]:
        x.ghostUpdate(addv=PETSc.InsertMode.INSERT_VALUES, mode=PETSc.ScatterMode.FORWARD)
        values = x.getArray(readonly=True)
        return {node: (float(values[dofs[0]]), float(values[dofs[1]])) for node, dofs in node_dofs.items()}

    def seed_admissible_opening(x) -> float:
        """Give the no-compression Newton iteration a non-physical feasible seed.

        A zero field lies on the opening constraint.  The prescribed top
        displacement can therefore have a locally closing first Newton
        direction even when an opening solution exists.  This strictly
        positive initial guess changes neither the case card nor the solved
        equilibrium; it only lets the feasibility-limited iteration begin in
        its declared domain.
        """
        seed_mm = max(1e-6, args.top_displacement_mm * 0.1)
        plus_nodes = {
            node for pair in pair_map["ordered_element_pairs"] for node in pair["plus"]["node_ids"]
        }
        minus_nodes = {
            node for pair in pair_map["ordered_element_pairs"] for node in pair["minus"]["node_ids"]
        }
        shared_nodes = plus_nodes & minus_nodes
        plus_nodes -= shared_nodes
        minus_nodes -= shared_nodes
        values = x.getArray()
        for nodes, sign in ((minus_nodes, -1.0), (plus_nodes, 1.0)):
            for node in nodes:
                dofs = node_dofs[node]
                values[dofs[0]] += sign * seed_mm * self_normal[0] / 2.0
                values[dofs[1]] += sign * seed_mm * self_normal[1] / 2.0
        x.assemblyBegin(); x.assemblyEnd()
        x.ghostUpdate(addv=PETSc.InsertMode.INSERT_VALUES, mode=PETSc.ScatterMode.FORWARD)
        if assembler.minimum_opening(pair_map, declared_displacements(x)) < 0.0:
            raise RuntimeError("admissible opening seed produced compression")
        return seed_mm

    def residual(_snes, x, f) -> None:
        bulk_matrix.mult(x, f)
        f.axpy(-1.0, rhs)
        _add_contribution(f, None, assembler.assemble(pair_map, declared_displacements(x)), node_dofs)
        f.assemblyBegin(); f.assemblyEnd()

    def tangent(_snes, x, J, P) -> None:
        J.setOption(PETSc.Mat.Option.NEW_NONZERO_ALLOCATION_ERR, False)
        J.zeroEntries(); J.axpy(1.0, bulk_matrix, structure=PETSc.Mat.Structure.SUBSET_NONZERO_PATTERN)
        J.setOption(PETSc.Mat.Option.NEW_NONZERO_ALLOCATION_ERR, False)
        _add_contribution(None, J, assembler.assemble(pair_map, declared_displacements(x)), node_dofs)
        J.assemblyBegin(); J.assemblyEnd()
        if P.handle != J.handle:
            P.zeroEntries(); P.axpy(1.0, J); P.assemblyBegin(); P.assemblyEnd()

    # petsc4py in the pinned DOLFINx image exposes no SNES line-search
    # precheck callback.  Keep PETSc for the linearized solve, but own the
    # compact Newton/backtracking loop here so the paired-lip module can cap a
    # candidate before *any* residual evaluation.  This is a feasibility
    # limiter, not a contact or complementarity formulation.
    ksp = PETSc.KSP().create(comm)
    ksp.setType("preonly")
    ksp.getPC().setType("lu")
    ksp.setOperators(jacobian)
    residual_history: list[float] = []
    current = displacement.x.petsc_vec
    self_normal = tuple(float(value) for value in pair_map["reference_trace"]["normal_minus_to_plus"])
    initial_opening_seed_mm = seed_admissible_opening(current)
    residual(None, current, residual_vector)
    initial_norm = residual_vector.norm()
    residual_history.append(float(initial_norm))
    newton_iterations = 0
    converged = initial_norm == 0.0
    for iteration in range(25):
        current_norm = residual_vector.norm()
        if current_norm <= initial_norm * 1e-8:
            converged = True
            break
        tangent(None, current, jacobian, jacobian)
        rhs_newton = residual_vector.copy()
        rhs_newton.scale(-1.0)
        update = current.duplicate()
        ksp.solve(rhs_newton, update)
        if ksp.getConvergedReason() <= 0:
            raise RuntimeError(f"PETSc Newton linear solve did not converge: reason {ksp.getConvergedReason()}")
        update.ghostUpdate(addv=PETSc.InsertMode.INSERT_VALUES, mode=PETSc.ScatterMode.FORWARD)
        update_values = update.getArray(readonly=True)
        increment = {
            node: (float(update_values[dofs[0]]), float(update_values[dofs[1]]))
            for node, dofs in node_dofs.items()
        }
        maximum_step = assembler.maximum_feasible_step(pair_map, declared_displacements(current), increment)
        if maximum_step <= 0.0:
            raise RuntimeError(
                "Newton direction has no positive no-compression step "
                f"(full-step minimum opening {assembler.minimum_opening(pair_map, {node: (current_value[0] + increment[node][0], current_value[1] + increment[node][1]) for node, current_value in declared_displacements(current).items()}):.12g} mm)"
            )
        step = maximum_step
        accepted = False
        for _ in range(20):
            candidate = current.copy()
            candidate.axpy(step, update)
            trial_residual = residual_vector.duplicate()
            # ``step`` is at or below the paired-lip feasibility cap, so this
            # is the first possible residual evaluation of the trial state.
            residual(None, candidate, trial_residual)
            trial_norm = trial_residual.norm()
            if trial_norm <= (1.0 - 1e-4 * step) * current_norm:
                candidate.copy(current)
                trial_residual.copy(residual_vector)
                residual_history.append(float(trial_norm))
                newton_iterations = iteration + 1
                accepted = True
                break
            step *= 0.5
        if not accepted:
            raise RuntimeError("feasibility-limited Newton backtracking exhausted")
    if not converged and residual_vector.norm() <= initial_norm * 1e-8:
        converged = True
    if not converged:
        raise RuntimeError(
            "PETSc feasibility-limited Newton solve did not converge within 25 iterations "
            f"(residual history tail: {residual_history[-5:]})"
        )
    final_displacements = declared_displacements(displacement.x.petsc_vec)
    final = assembler.assemble(pair_map, final_displacements)
    relative_residual = 0.0 if not residual_history or residual_history[0] == 0.0 else residual_history[-1] / residual_history[0]
    stress = _stress(domain, displacement, youngs, poisson)
    strain = ufl.sym(ufl.grad(displacement))
    normal = ufl.FacetNormal(domain)
    ds = ufl.Measure("ds", domain=domain, subdomain_data=facet_tags)
    reaction = _scalar(
        domain,
        ufl.dot(ufl.dot(stress, normal), ufl.as_vector((0.0, 1.0))) * ds(physical_groups["loaded"].tag),
    )
    bulk_strain_energy = _scalar(domain, 0.5 * ufl.inner(stress, strain) * ufl.dx)
    j_diagnostic = [
        {"radius_mm": radius, "j_mpa_mm": _domain_integral_j(domain, displacement, radius, youngs, poisson)}
        for radius in card["fracture_quantity"]["contour_radii_mm"]
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    if comm.rank == 0:
        (args.output / "reversible-cohesive-step.json").write_text(json.dumps({
            "case_id": card["case_id"], "status": "solved-single-displacement-step",
            "top_displacement_mm": args.top_displacement_mm, "newton_iterations": newton_iterations,
            "initial_opening_seed_mm": initial_opening_seed_mm,
            "relative_residual": relative_residual, "residual_history": residual_history,
            "mouth_opening_mm": _mouth_opening_mm(pair_map, final_displacements),
            "minimum_normal_opening_mm": assembler.minimum_opening(pair_map, final_displacements),
            "reversible_interface_potential_mpa_mm2": final.reversible_potential_mpa_mm2,
            "quadrature_subintervals": final.quadrature_subintervals,
            "diagnostics": {
                "reaction": {"status": "computed", "value_mpa_mm": reaction,
                             "convention": "positive y traction resultant on the loaded exterior"},
                "bulk_strain_energy": {"status": "computed", "value_mpa_mm2": bulk_strain_energy},
                "j": {"status": "diagnostic-only", "method": "domain-integral", "direction": "crack-extension-x",
                      "contours": j_diagnostic,
                      "claim_boundary": "No toughness or fracture-energy comparison or authority is implied."},
            },
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

import { expect, test } from "bun:test";

import { createSimulationClient } from "./simulation-client";

const envelope = {
	api_version: "v1",
	fixture: {
		case_id: "sic-sic-panel-042",
		corpus_id: "v1-demo-2026-08",
		kind: "representative",
		revision: "1",
	},
	provenance: {
		claim_boundary:
			"Comparison evidence within the declared numerical model; not experimental truth or a qualified structural prediction.",
		reference_solution: {
			discretization_id: "demo-mesh-r1",
			model_id: "demo-cmc-fracture-model",
			solver_configuration_id: "demo-config-r1",
		},
		source_kind: "fixture",
	},
};

test("submits a declared fixture reference run through the API transport", async () => {
	const requests: unknown[] = [];
	const client = createSimulationClient({
		request: async (request) => {
			requests.push(request);
			return {
				status: 202,
				body: {
					...envelope,
					run: {
						run_id: "run-0001",
						case_id: "sic-sic-panel-042",
						status: "queued",
					},
				},
			};
		},
	});

	const response = await client.submitReferenceRun({
		caseId: "sic-sic-panel-042",
		inputs: {
			coatingShearLimitMpa: 60,
			mechanicalLoadKn: 45,
			thermalGradientCPerMm: 120,
		},
	});

	expect(requests).toEqual([
		{
			method: "POST",
			path: "/api/v1/reference-runs",
			body: {
				case_id: "sic-sic-panel-042",
				inputs: {
					coating_shear_limit_mpa: 60,
					mechanical_load_kn: 45,
					thermal_gradient_c_per_mm: 120,
				},
			},
		},
	]);
	expect(response).toEqual({
		fixture: {
			caseId: "sic-sic-panel-042",
			corpusId: "v1-demo-2026-08",
			kind: "representative",
			revision: "1",
		},
		provenance: {
			claimBoundary: envelope.provenance.claim_boundary,
			referenceSolution: {
				discretizationId: "demo-mesh-r1",
				modelId: "demo-cmc-fracture-model",
				solverConfigurationId: "demo-config-r1",
			},
			sourceKind: "fixture",
		},
		run: { runId: "run-0001", caseId: "sic-sic-panel-042", status: "queued" },
	});
});

test("rejects a reference-run submission response that is not queued", async () => {
	const client = createSimulationClient({
		request: async () => ({
			status: 202,
			body: {
				...envelope,
				run: {
					run_id: "run-0001",
					case_id: "sic-sic-panel-042",
					status: "complete",
				},
			},
		}),
	});

	await expect(
		client.submitReferenceRun(referenceRunSubmission),
	).rejects.toThrow("Fixture reference-run response was malformed.");
});

test("rejects a response that drops required V1 provenance", async () => {
	const client = createSimulationClient({
		request: async () => ({
			status: 202,
			body: {
				...envelope,
				provenance: { source_kind: "fixture" },
				run: {
					run_id: "run-0001",
					case_id: "sic-sic-panel-042",
					status: "queued",
				},
			},
		}),
	});

	await expect(
		client.submitReferenceRun(referenceRunSubmission),
	).rejects.toThrow("Fixture response was malformed.");
});

test("rejects a reference-run submission response without the common envelope", async () => {
	const client = createSimulationClient({
		request: async () => ({
			status: 202,
			body: {
				run: {
					run_id: "run-0001",
					case_id: "sic-sic-panel-042",
					status: "queued",
				},
			},
		}),
	});

	await expect(
		client.submitReferenceRun(referenceRunSubmission),
	).rejects.toThrow("Fixture response was malformed.");
});

test("observes a fixture run and reads its representative result through the API transport", async () => {
	const requests: unknown[] = [];
	const client = createSimulationClient({
		request: async (request) => {
			requests.push(request);
			if (request.path.endsWith("/results")) {
				return {
					status: 200,
					body: {
						...envelope,
						result: {
							quantity: "j_integral_proxy",
							value: 12.4,
							units: "J/m²",
						},
					},
				};
			}
			return {
				status: 200,
				body: {
					...envelope,
					run: {
						run_id: "run-0001",
						case_id: "sic-sic-panel-042",
						status: "complete",
					},
				},
			};
		},
	});

	expect(await client.getReferenceRun("run-0001")).toMatchObject({
		run: { runId: "run-0001", status: "complete" },
	});
	expect(await client.getReferenceRunResult("run-0001")).toMatchObject({
		result: { quantity: "j_integral_proxy", value: 12.4, units: "J/m²" },
	});
	expect(requests).toEqual([
		{ method: "GET", path: "/api/v1/reference-runs/run-0001", body: undefined },
		{
			method: "GET",
			path: "/api/v1/reference-runs/run-0001/results",
			body: undefined,
		},
	]);
});

test("rejects missing provenance on a reference result", async () => {
	const client = createSimulationClient({
		request: async () => ({
			status: 200,
			body: {
				...envelope,
				provenance: { source_kind: "fixture" },
				result: { quantity: "j_integral_proxy", units: "J/m²", value: 12.4 },
			},
		}),
	});

	await expect(client.getReferenceRunResult("run-0001")).rejects.toThrow(
		"Fixture response was malformed.",
	);
});

test("submits a declared fixture surrogate observation through the API transport", async () => {
	const requests: unknown[] = [];
	const client = createSimulationClient({
		request: async (request) => {
			requests.push(request);
			return {
				status: 201,
				body: {
					...envelope,
					provenance: {
						...envelope.provenance,
						claim_boundary:
							"Fixture adjudication only; not independent physical validation or qualification.",
						surrogate: { domain_id: "demo-domain-r1", model_id: "demo-fno-r1" },
					},
					verification: {
						quantity: "j_integral_proxy",
						reference_value: 12.4,
						relative_error: 0.0242,
						status: "accepted",
						surrogate_value: 12.1,
						units: "J/m²",
						verification_id: "verification-0001",
					},
				},
			};
		},
	});

	expect(
		await client.verifySurrogateObservation(
			"run-0001",
			referenceRunSubmission,
			{
				quantity: "j_integral_proxy",
				units: "J/m²",
				value: 12.1,
			},
		),
	).toMatchObject({
		provenance: {
			claimBoundary:
				"Fixture adjudication only; not independent physical validation or qualification.",
			surrogate: { domainId: "demo-domain-r1", modelId: "demo-fno-r1" },
		},
		verification: { status: "accepted", verificationId: "verification-0001" },
	});
	expect(requests).toEqual([
		{
			method: "POST",
			path: "/api/v1/simulation/verify",
			body: {
				reference_run_id: "run-0001",
				inputs: {
					coating_shear_limit_mpa: 60,
					mechanical_load_kn: 45,
					thermal_gradient_c_per_mm: 120,
				},
				observation: {
					quantity: "j_integral_proxy",
					units: "J/m²",
					value: 12.1,
				},
			},
		},
	]);
});

test("rejects malformed optional surrogate provenance", async () => {
	const client = createSimulationClient({
		request: async () => ({
			status: 201,
			body: {
				...envelope,
				provenance: {
					...envelope.provenance,
					surrogate: { domain_id: "demo-domain-r1", model_id: 42 },
				},
				verification: {
					quantity: "j_integral_proxy",
					reference_value: 12.4,
					relative_error: 0.0242,
					status: "accepted",
					surrogate_value: 12.1,
					units: "J/m²",
					verification_id: "verification-0001",
				},
			},
		}),
	});

	await expect(
		client.verifySurrogateObservation("run-0001", referenceRunSubmission, {
			quantity: "j_integral_proxy",
			units: "J/m²",
			value: 12.1,
		}),
	).rejects.toThrow("Fixture response was malformed.");
});

const referenceRunSubmission = {
	caseId: "sic-sic-panel-042",
	inputs: {
		coatingShearLimitMpa: 60,
		mechanicalLoadKn: 45,
		thermalGradientCPerMm: 120,
	},
};

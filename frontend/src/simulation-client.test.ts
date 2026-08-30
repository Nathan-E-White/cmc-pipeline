import { expect, test } from "bun:test"

import { createSimulationClient } from "./simulation-client"

test("submits a declared fixture reference run through the API transport", async () => {
	const requests: unknown[] = []
	const client = createSimulationClient({
		request: async (request) => {
			requests.push(request)
			return {
				status: 202,
				body: {
					api_version: "v1",
					fixture: { corpus_id: "v1-demo-2026-08", kind: "representative" },
					provenance: { source_kind: "fixture" },
					run: {
						run_id: "run-0001",
						case_id: "sic-sic-panel-042",
						status: "queued",
					},
				},
			}
		},
	})

	const response = await client.submitReferenceRun({
		caseId: "sic-sic-panel-042",
		inputs: {
			coatingShearLimitMpa: 60,
			mechanicalLoadKn: 45,
			thermalGradientCPerMm: 120,
		},
	})

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
	])
	expect(response).toEqual({
		fixture: { corpusId: "v1-demo-2026-08", kind: "representative" },
		provenance: { sourceKind: "fixture" },
		run: { runId: "run-0001", caseId: "sic-sic-panel-042", status: "queued" },
	})
})

test("rejects a reference-run submission response that is not queued", async () => {
	const client = createSimulationClient({
		request: async () => ({
			status: 202,
			body: {
				api_version: "v1",
				fixture: { corpus_id: "v1-demo-2026-08", kind: "representative" },
				provenance: { source_kind: "fixture" },
				run: { run_id: "run-0001", case_id: "sic-sic-panel-042", status: "complete" },
			},
		}),
	})

	await expect(client.submitReferenceRun(referenceRunSubmission)).rejects.toThrow(
		"Fixture reference-run response was malformed.",
	)
})

test("rejects a reference-run submission response without the common envelope", async () => {
	const client = createSimulationClient({
		request: async () => ({
			status: 202,
			body: {
				run: { run_id: "run-0001", case_id: "sic-sic-panel-042", status: "queued" },
			},
		}),
	})

	await expect(client.submitReferenceRun(referenceRunSubmission)).rejects.toThrow(
		"Fixture reference-run response was malformed.",
	)
})

const referenceRunSubmission = {
	caseId: "sic-sic-panel-042",
	inputs: {
		coatingShearLimitMpa: 60,
		mechanicalLoadKn: 45,
		thermalGradientCPerMm: 120,
	},
}

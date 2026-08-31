import { render, screen, waitFor } from "@solidjs/testing-library";
import { createComponent } from "solid-js";
import { expect, test } from "vitest";

import { ReferenceRunControls } from "./ReferenceRunControls";

const fixture = {
	caseId: "sic-sic-panel-042",
	corpusId: "v1-demo-2026-08",
	kind: "representative" as const,
	revision: "1",
};
const provenance = {
	claimBoundary:
		"Comparison evidence within the declared numerical model; not experimental truth or a qualified structural prediction.",
	referenceSolution: {
		discretizationId: "demo-mesh-r1",
		modelId: "demo-cmc-fracture-model",
		solverConfigurationId: "demo-config-r1",
	},
	sourceKind: "fixture" as const,
};

test("submits, observes, and renders a representative fixture reference result", async () => {
	const verificationRequests: unknown[][] = [];
	const client = {
		submitReferenceRun: async () => ({
			fixture,
			provenance,
			run: {
				caseId: "sic-sic-panel-042",
				runId: "run-0001",
				status: "queued" as const,
			},
		}),
		getReferenceRun: async () => ({
			fixture,
			provenance,
			run: {
				caseId: "sic-sic-panel-042",
				runId: "run-0001",
				status: "complete" as const,
			},
		}),
		getReferenceRunResult: async () => ({
			fixture,
			provenance,
			result: { quantity: "j_integral_proxy", units: "J/m²", value: 12.4 },
		}),
		verifySurrogateObservation: async (...request: unknown[]) => {
			verificationRequests.push(request);
			return {
				fixture,
				provenance: {
					...provenance,
					claimBoundary:
						"Fixture adjudication only; not independent physical validation or qualification.",
					surrogate: { domainId: "demo-domain-r1", modelId: "demo-fno-r1" },
				},
				verification: {
					quantity: "j_integral_proxy",
					referenceValue: 12.4,
					relativeError: 0.0242,
					status: "accepted" as const,
					surrogateValue: 12.1,
					units: "J/m²",
					verificationId: "verification-0001",
				},
			};
		},
	};

	render(() =>
		createComponent(ReferenceRunControls, {
			client,
			submission: {
				caseId: "sic-sic-panel-042",
				inputs: {
					coatingShearLimitMpa: 60,
					mechanicalLoadKn: 45,
					thermalGradientCPerMm: 120,
				},
			},
		}),
	);
	expect(
		screen.getByText("No fixture records in this browser session."),
	).toBeTruthy();

	const submit = screen.getByRole<HTMLButtonElement>("button", {
		name: "Record fixture reference run",
	});
	submit.click();
	await waitFor(() => {
		expect(screen.getByText("Complete fixture reference run")).toBeTruthy();
		expect(screen.getByText("j_integral_proxy: 12.4 J/m²")).toBeTruthy();
		expect(screen.getByText("Accepted fixture adjudication")).toBeTruthy();
		expect(screen.getByText(provenance.claimBoundary)).toBeTruthy();
		expect(
			screen.getByText(
				"demo-cmc-fracture-model · demo-config-r1 · demo-mesh-r1",
			),
		).toBeTruthy();
		expect(
			screen.getByText(
				"Fixture adjudication only; not independent physical validation or qualification.",
			),
		).toBeTruthy();
		expect(verificationRequests).toEqual([
			[
				"run-0001",
				{
					caseId: "sic-sic-panel-042",
					inputs: {
						coatingShearLimitMpa: 60,
						mechanicalLoadKn: 45,
						thermalGradientCPerMm: 120,
					},
				},
				{ quantity: "j_integral_proxy", units: "J/m²", value: 12.1 },
			],
		]);
	});
	submit.click();
	await waitFor(() => {
		expect(screen.getAllByText("Complete fixture reference run")).toHaveLength(
			2,
		);
		expect(verificationRequests).toHaveLength(2);
	});
});

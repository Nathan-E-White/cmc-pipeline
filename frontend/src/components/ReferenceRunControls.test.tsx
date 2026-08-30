import { render, screen, waitFor } from "@solidjs/testing-library";
import { createComponent } from "solid-js";
import { expect, test } from "vitest";

import { ReferenceRunControls } from "./ReferenceRunControls";

test("submits, observes, and renders a representative fixture reference result", async () => {
	const verificationRequests: unknown[][] = [];
	const client = {
		submitReferenceRun: async () => ({
			fixture: { corpusId: "v1-demo-2026-08", kind: "representative" as const },
			provenance: { sourceKind: "fixture" as const },
			run: {
				caseId: "sic-sic-panel-042",
				runId: "run-0001",
				status: "queued" as const,
			},
		}),
		getReferenceRun: async () => ({
			fixture: { corpusId: "v1-demo-2026-08", kind: "representative" as const },
			provenance: { sourceKind: "fixture" as const },
			run: {
				caseId: "sic-sic-panel-042",
				runId: "run-0001",
				status: "complete" as const,
			},
		}),
		getReferenceRunResult: async () => ({
			fixture: { corpusId: "v1-demo-2026-08", kind: "representative" as const },
			provenance: { sourceKind: "fixture" as const },
			result: { quantity: "j_integral_proxy", units: "J/m²", value: 12.4 },
		}),
		verifySurrogateObservation: async (...request: unknown[]) => {
			verificationRequests.push(request);
			return {
				fixture: {
					corpusId: "v1-demo-2026-08",
					kind: "representative" as const,
				},
				provenance: {
					claimBoundary:
						"Fixture adjudication only; not independent physical validation or qualification.",
					sourceKind: "fixture" as const,
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

	screen
		.getByRole<HTMLButtonElement>("button", {
			name: "Submit fixture reference run",
		})
		.click();
	await waitFor(() => {
		expect(screen.getByText("Complete fixture reference run")).toBeTruthy();
		expect(screen.getByText("j_integral_proxy: 12.4 J/m²")).toBeTruthy();
		expect(screen.getByText("Accepted fixture comparison")).toBeTruthy();
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
});

import { render } from "@solidjs/testing-library";
import { describe, expect, it } from "vitest";
import { parseFieldArtifact } from "../field-artifact";
import { FieldViewer } from "./FieldViewer";

describe("FieldViewer", () => {
	it("renders geometry, units, and provenance only for an available payload", () => {
		const screen = render(() => (
			<FieldViewer
				response={{
					version: "cmc.field-artifact.v1",
					state: "available",
					payload: {
						geometry: {
							positions: [
								[0, 0],
								[1, 0],
								[0, 1],
							],
							triangles: [[0, 1, 2]],
						},
						field: {
							id: "displacement",
							name: "displacement_mm",
							units: "mm",
							association: "node",
							components: 2,
							values: [
								[0, 0],
								[0, 0],
								[0, 0],
							],
						},
						provenance: {
							run_id: "run-1",
							case_digest: "case-1",
							outcome: "solved",
							evidence_disposition: "accepted",
							claim_boundary: "Local reference only.",
							artifact_digests: { "field-set-manifest": "abc123" },
						},
					},
				}}
			/>
		));
		expect(
			screen.getByRole("img", { name: "displacement_mm field in mm" }),
		).toBeTruthy();
		expect(screen.getByText(/run: run-1/)).toBeTruthy();
		expect(screen.getByText(/Magnitude legend: 0.000–0.000 mm/)).toBeTruthy();
		expect(screen.getByText(/boundary: Local reference only/)).toBeTruthy();
		expect(screen.getByText(/field-set-manifest:abc123/)).toBeTruthy();
	});

	it("does not render a field for indeterminate evidence", () => {
		const screen = render(() => (
			<FieldViewer
				response={{
					version: "cmc.field-artifact.v1",
					state: "indeterminate",
					reason: "run_not_accepted",
					provenance: {
						run_id: "run-1",
						case_digest: "case-1",
						outcome: "indeterminate",
						evidence_disposition: "indeterminate",
					},
				}}
			/>
		));
		expect(screen.queryByRole("img")).toBeNull();
		expect(screen.getByText("indeterminate: run_not_accepted")).toBeTruthy();
	});

	it("rejects an unknown response version before it reaches the viewer", () => {
		expect(() =>
			parseFieldArtifact({ version: "cmc.field-artifact.v2" }),
		).toThrow("Unsupported field artifact version.");
	});
});

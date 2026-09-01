import { render, screen } from "@solidjs/testing-library";
import { createComponent } from "solid-js";
import { expect, test } from "vitest";

import { EvidenceSummary } from "./EvidenceSummary";

test("reveals only a bounded readable diagnostic preview and terminal copy action", async () => {
	render(() =>
		createComponent(EvidenceSummary, {
			phase: "Newton solve",
			state: "running",
			headline: "4 / 25",
			residuals: [1, 0.1, 0.01],
			containerObservedAt: "2 s ago",
			solverEvidenceAt: "4 s ago",
			details: Array.from({ length: 6 }, (_, index) => ({
				label: `Iteration ${index + 1}`,
				value: "observed",
			})),
		}),
	);
	const toggle = screen.getByRole("button", { name: /Newton solve/ });
	expect(toggle.getAttribute("aria-expanded")).toBe("false");
	toggle.click();
	expect(toggle.getAttribute("aria-expanded")).toBe("true");
	expect(screen.getAllByText("observed")).toHaveLength(5);
	expect(screen.queryByRole("button", { name: /Copy complete/ })).toBeNull();
});

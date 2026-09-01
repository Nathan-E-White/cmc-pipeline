import { render, screen } from "@solidjs/testing-library";
import { createComponent } from "solid-js";
import { expect, test, vi } from "vitest";

import { EvidenceSummary } from "./EvidenceSummary";

test("reveals only a bounded readable diagnostic preview and terminal copy action", async () => {
	const loadOlder = vi.fn(async () => undefined);
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
			hasOlder: true,
			loadOlder,
		}),
	);
	const toggle = screen.getByRole("button", { name: /Newton solve/ });
	expect(toggle.getAttribute("aria-expanded")).toBe("false");
	toggle.click();
	expect(toggle.getAttribute("aria-expanded")).toBe("true");
	expect(screen.getAllByText("observed")).toHaveLength(5);
	screen.getByRole("button", { name: "Load older evidence" }).click();
	expect(loadOlder).toHaveBeenCalledOnce();
	expect(screen.queryByRole("button", { name: /Copy complete/ })).toBeNull();
});

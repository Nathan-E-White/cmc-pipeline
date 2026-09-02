import { expect, test } from "bun:test";

const monitor = await Bun.file("monitor/src/components/V3RunRegister.tsx").text();
const appSources = await Promise.all([
	Bun.file("app/src/components/FieldViewer.tsx").text(),
	Bun.file("app/src/routes/runs.$runId.tsx").text(),
]);

test("monitor links to results but cannot render or subscribe to it", () => {
	expect(monitor).toContain("View physics result");
	expect(monitor).not.toContain("FieldViewer");
	expect(monitor).not.toContain("RunFieldViewer");
});

test("results app has no Electric or SSE monitor transport", () => {
	expect(appSources.join("\n")).not.toContain("@electric-sql/client");
	expect(appSources.join("\n")).not.toContain("EventSource");
});

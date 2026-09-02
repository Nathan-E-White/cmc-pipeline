import { expect, test } from "bun:test";

async function sourceTree(directory: "app" | "monitor") {
	const files = new Bun.Glob(`${directory}/src/**/*.{ts,tsx}`);
	const sources = await Promise.all(
		Array.from(files.scanSync(".")).map(async (path) => ({
			path,
			text: await Bun.file(path).text(),
		})),
	);
	return sources;
}

test("monitor source owns operational transport and cannot render results", async () => {
	const monitorSources = await sourceTree("monitor");
	expect(monitorSources.some(({ text }) => text.includes("View physics result"))).toBe(true);
	for (const { path, text } of monitorSources) {
		expect(text, path).not.toContain("FieldViewer");
		expect(text, path).not.toContain("RunFieldViewer");
		expect(text, path).not.toMatch(/(?:\.\.\/)+app\//);
	}
});

test("results source has no Electric, SSE, or monitor imports", async () => {
	for (const { path, text } of await sourceTree("app")) {
		expect(text, path).not.toContain("@electric-sql/client");
		expect(text, path).not.toContain("EventSource");
		expect(text, path).not.toMatch(/(?:\.\.\/)+monitor\//);
	}
});

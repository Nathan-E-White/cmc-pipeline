import { chromium } from "playwright";

const origin = process.env.CMC_MONITOR_ORIGIN ?? "http://127.0.0.1:3000";

async function readyFetch(path) {
	let lastError;
	for (let attempt = 0; attempt < 20; attempt += 1) {
		try {
			return await fetch(`${origin}${path}`);
		} catch (error) {
			lastError = error;
			await Bun.sleep(100);
		}
	}
	throw new Error(`Monitor container did not become reachable: ${lastError}`);
}

const snapshotResponse = await readyFetch("/api/v3/runs");
if (!snapshotResponse.ok) {
	throw new Error(`Monitor API proxy returned ${snapshotResponse.status}.`);
}
const snapshot = await snapshotResponse.json();
if (!Array.isArray(snapshot.runs) || snapshot.runs.length === 0) {
	throw new Error("Container monitor check requires one persisted run summary.");
}

const electricResponse = await readyFetch(
	"/electric/v1/shape?table=run_summary_projections&offset=-1",
);
if (!electricResponse.ok) {
	throw new Error(
		`Monitor Electric proxy returned ${electricResponse.status}: ${await electricResponse.text()}`,
	);
}

const response = await readyFetch("/");
if (!response.ok) {
	throw new Error(`Monitor container route returned ${response.status}.`);
}
const html = await response.text();
for (const expected of [
	"<title>CMC Pipeline Monitor</title>",
	"Operational run ribbon",
	`aria-label=\"Run ${snapshot.runs[0].run_id}\"`,
]) {
	if (!html.includes(expected)) {
		throw new Error(`Container monitor SSR response is missing: ${expected}`);
	}
}

const browser = await chromium.launch({ headless: true });
try {
	const page = await browser.newPage();
	await page.goto(`${origin}/`, { waitUntil: "networkidle" });
	await page
		.getByRole("article", { name: `Run ${snapshot.runs[0].run_id}` })
		.waitFor();
	await page.waitForTimeout(250);
	if (
		(await page.getByRole("article", { name: `Run ${snapshot.runs[0].run_id}` }).count()) !==
		1
	) {
		throw new Error("Hydrated monitor did not retain its SSR run article.");
	}
} finally {
	await browser.close();
}

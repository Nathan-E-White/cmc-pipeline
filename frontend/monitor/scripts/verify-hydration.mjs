import { chromium } from "playwright";

const port = 3104;
const server = Bun.spawn([process.execPath, "dist/server/server.js"], {
	cwd: import.meta.dir + "/..",
	env: { ...process.env, PORT: String(port) },
	stdout: "ignore",
	stderr: "pipe",
});

try {
	for (let attempt = 0; attempt < 20; attempt += 1) {
		try {
			const response = await fetch(`http://127.0.0.1:${port}/`);
			if (response.status === 200) break;
		} catch {
			await Bun.sleep(50);
		}
	}

	const browser = await chromium.launch({ headless: true });
	try {
		const page = await browser.newPage();
		const warnings = [];
		page.on("console", (message) => {
			if (message.type() === "warning" || message.type() === "error") {
				warnings.push(message.text());
			}
		});
		await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
		await page.getByRole("heading", { name: "Operational run ribbon" }).waitFor();
		const mismatch = warnings.find((warning) =>
			warning.includes("Hydration Mismatch"),
		);
		if (mismatch) throw new Error(`Monitor hydration mismatch: ${mismatch}`);
	} finally {
		await browser.close();
	}
} finally {
	server.kill();
}

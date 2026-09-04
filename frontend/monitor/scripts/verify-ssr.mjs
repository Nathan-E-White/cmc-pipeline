const port = 3103;
const server = Bun.spawn([process.execPath, "dist/server/server.js"], {
	cwd: import.meta.dir + "/..",
	env: { ...process.env, PORT: String(port) },
	stdout: "ignore",
	stderr: "pipe",
});

try {
	let response;
	for (let attempt = 0; attempt < 20; attempt += 1) {
		try {
			response = await fetch(`http://127.0.0.1:${port}/`);
			break;
		} catch {
			await Bun.sleep(50);
		}
	}

	if (!response) {
		const error = await new Response(server.stderr).text();
		throw new Error(`Monitor SSR server did not start.\n${error}`);
	}
	if (response.status !== 200) {
		throw new Error(`Monitor SSR route returned ${response.status}.`);
	}
	const html = await response.text();
	for (const expected of [
		"<title>CMC Pipeline Monitor</title>",
		"Operational run ribbon",
		"V3 operational run register",
	]) {
		if (!html.includes(expected)) {
			throw new Error(`Monitor SSR shell is missing: ${expected}`);
		}
	}
} finally {
	server.kill();
}

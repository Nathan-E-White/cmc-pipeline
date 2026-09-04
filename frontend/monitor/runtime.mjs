import monitorServer from "./dist/server/server.js";

const backendOrigin = process.env.CMC_BACKEND_ORIGIN ?? "http://backend:8000";
const electricOrigin = process.env.CMC_ELECTRIC_ORIGIN ?? "http://electric:3000";

function forward(request, origin, stripPrefix = "") {
	const incoming = new URL(request.url);
	const pathname = stripPrefix
		? (incoming.pathname.slice(stripPrefix.length) || "/")
		: incoming.pathname;
	const target = new URL(`${pathname}${incoming.search}`, origin);
	const headers = new Headers(request.headers);
	headers.delete("host");
	return fetch(
		new Request(target, {
			method: request.method,
			headers,
			body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
		}),
	);
}

Bun.serve({
	hostname: "0.0.0.0",
	port: Number(process.env.PORT ?? 3000),
	fetch(request) {
		const pathname = new URL(request.url).pathname;
		if (pathname.startsWith("/api/")) return forward(request, backendOrigin);
		if (pathname.startsWith("/electric/")) {
			return forward(request, electricOrigin, "/electric");
		}
		return monitorServer.fetch(request);
	},
});

import { createFileRoute } from "@tanstack/solid-router";
import {
	type RunRegisterSnapshot,
	V3RunRegister,
} from "../components/V3RunRegister";

const snapshotUnavailable = "Run register snapshot unavailable.";
const serverEnvironment = globalThis as typeof globalThis & {
	process?: { env?: Record<string, string | undefined> };
};

async function initialRunRegister(): Promise<RunRegisterSnapshot> {
	try {
		const origin =
			typeof window === "undefined"
				? (serverEnvironment.process?.env?.CMC_BACKEND_ORIGIN ??
					"http://127.0.0.1:8000")
				: window.location.origin;
		const response = await fetch(new URL("/api/v3/runs", origin), {
			signal: AbortSignal.timeout(2_000),
		});
		if (!response.ok) throw new Error(snapshotUnavailable);
		const payload = (await response.json()) as Partial<RunRegisterSnapshot>;
		if (
			!Array.isArray(payload.runs) ||
			typeof payload.register_sequence !== "number"
		) {
			throw new Error(snapshotUnavailable);
		}
		return { runs: payload.runs, register_sequence: payload.register_sequence };
	} catch {
		return {
			runs: [],
			register_sequence: 0,
			unavailableReason: snapshotUnavailable,
		};
	}
}

export const Route = createFileRoute("/")({
	loader: initialRunRegister,
	component: Home,
});

function Home() {
	return <V3RunRegister initialSnapshot={Route.useLoaderData()()} />;
}

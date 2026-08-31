import { createFileRoute } from "@tanstack/solid-router";
import { RunRegisterPrototype } from "../components/RunRegisterPrototype";
import type { RegisterVariant } from "../prototypes/run-register";

// PROTOTYPE: three run-register layouts, switchable by ?variant=.
export const Route = createFileRoute("/")({
	component: Home,
	validateSearch: (search: Record<string, unknown>) => ({
		variant: isVariant(search.variant) ? search.variant : "paintbox",
	}),
});

function Home() {
	const search = Route.useSearch();
	return <RunRegisterPrototype variant={search().variant} />;
}

function isVariant(value: unknown): value is RegisterVariant {
	return value === "paintbox" || value === "ledger" || value === "sequence";
}

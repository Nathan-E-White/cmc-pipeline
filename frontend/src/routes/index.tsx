import { createFileRoute } from "@tanstack/solid-router";
import { ReferenceRunControls } from "../components/ReferenceRunControls";
import { V3RunRegister } from "../components/V3RunRegister";
import { simulationClient } from "../simulation-client";

export const Route = createFileRoute("/")({
	component: Home,
});

function Home() {
	return (
		<>
			<V3RunRegister />
			<ReferenceRunControls client={simulationClient} />
		</>
	);
}

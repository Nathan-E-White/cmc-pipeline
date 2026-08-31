import { createFileRoute } from "@tanstack/solid-router";
import { ReferenceRunControls } from "../components/ReferenceRunControls";
import { simulationClient } from "../simulation-client";

export const Route = createFileRoute("/")({
	component: Home,
});

function Home() {
	return (
		<ReferenceRunControls
			client={simulationClient}
			submission={{
				caseId: "sic-sic-panel-042",
				inputs: {
					coatingShearLimitMpa: 60,
					mechanicalLoadKn: 45,
					thermalGradientCPerMm: 120,
				},
			}}
		/>
	);
}

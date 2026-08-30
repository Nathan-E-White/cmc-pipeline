import { createFileRoute } from "@tanstack/solid-router";
import { createSignal, Show } from "solid-js";

import { ControlPanel } from "../components/ControlPanel";
import { ReferenceRunControls } from "../components/ReferenceRunControls";
import { ThreeViewport } from "../components/ThreeViewport";
import {
	defaultInputs,
	nodeCountFor,
	type SimulationInput,
	type SimulationSnapshot,
} from "../simulation";
import { simulationClient } from "../simulation-client";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
	const [inputs, setInputs] = createSignal(defaultInputs);
	const [snapshot, setSnapshot] = createSignal<SimulationSnapshot>(
		idle(inputs()),
	);
	const update = (value: Partial<SimulationInput>) => {
		const next = { ...inputs(), ...value };
		setInputs(next);
		setSnapshot(idle(next));
	};
	return (
		<main class="app-shell">
			<ControlPanel inputs={inputs} onInput={update} snapshot={snapshot} />
			<Show
				fallback={
					<p>Reference-run fixture unavailable for this architecture.</p>
				}
				when={referenceRunSubmission(inputs())}
			>
				{(submission) => (
					<ReferenceRunControls
						client={simulationClient}
						submission={submission()}
					/>
				)}
			</Show>
			<ThreeViewport snapshot={snapshot} />
		</main>
	);
}

function idle(inputs: SimulationInput): SimulationSnapshot {
	return {
		mode: "Representative material continuum",
		progress: 0,
		runs: { FEA: undefined, FNO: undefined },
		status: "idle",
		telemetry: {
			area: 0,
			energy: 0,
			margin: 1.5,
			nodes: nodeCountFor(inputs.architecture),
		},
		title: "System ready",
	};
}

function referenceRunSubmission(inputs: SimulationInput) {
	if (inputs.architecture !== "sic_sic") return undefined;
	return {
		caseId: "sic-sic-panel-042",
		inputs: {
			coatingShearLimitMpa: inputs.coatingStrength,
			mechanicalLoadKn: inputs.mechanicalLoad,
			thermalGradientCPerMm: inputs.thermalGradient,
		},
	};
}

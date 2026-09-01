import { For } from "solid-js";

import { EvidenceSummary } from "./EvidenceSummary";

const phases = [
	{ key: "admitted", label: "Admitted", state: "completed" },
	{ key: "mesh", label: "Mesh", state: "completed" },
	{ key: "solve", label: "Solve", state: "running" },
	{ key: "adjudicate", label: "Adjudicate", state: "pending" },
	{ key: "publish", label: "Publish", state: "pending" },
] as const;

export function V3RunRegister() {
	return (
		<section class="v3-run-register" aria-label="V3 operational run register">
			<header>
				<p class="eyebrow">CMC Pipeline · V3 local-development projection</p>
				<h2>Operational run ribbon</h2>
				<p>
					Presentation prototype. It does not claim a live solver until the
					executor is connected.
				</p>
			</header>
			<ol class="run-ribbon" aria-label="R0 reference run phases">
				<For each={phases}>
					{(phase) => (
						<li class={`run-ribbon-phase ${phase.state}`}>{phase.label}</li>
					)}
				</For>
			</ol>
			<EvidenceSummary
				phase="Newton solve"
				state="running"
				headline="4 / 25 · residual 1.0e-4"
				containerObservedAt="2 s ago"
				solverEvidenceAt="4 s ago"
				residuals={[1, 0.18, 0.032, 0.001]}
				details={[
					{ label: "Iteration 1", value: "residual 1.0e0" },
					{ label: "Iteration 2", value: "residual 1.8e-1" },
					{ label: "Iteration 3", value: "residual 3.2e-2" },
					{ label: "Iteration 4", value: "residual 1.0e-3" },
				]}
			/>
		</section>
	);
}

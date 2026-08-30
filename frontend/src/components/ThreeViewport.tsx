import type { Accessor } from "solid-js";

import type { SimulationSnapshot } from "../simulation";

export function ThreeViewport(props: {
	snapshot: Accessor<SimulationSnapshot>;
}) {
	const snapshot = props.snapshot;
	const marginTone = () =>
		snapshot().telemetry.margin < 0
			? "danger"
			: snapshot().telemetry.margin < 0.3
				? "warning"
				: "success";
	return (
		<section
			class="viewport"
			aria-label="Representative fracture field viewport"
		>
			<header>
				<div>
					<small>Material continuum</small>
					<h1>{snapshot().title}</h1>
				</div>
				<p>{snapshot().mode}</p>
			</header>
			<div class="field-view">
				<div class="material">
					<i />
					<i />
					<i />
					<i />
					<div
						class="crack"
						style={{ width: `${snapshot().progress * 78}%` }}
					/>
				</div>
				<span>Representative field view — rendering adapter pending</span>
			</div>
			<div class="telemetry">
				<Datum label="Micro-FE nodes" value={snapshot().telemetry.nodes} />
				<Datum
					label="Energy-release proxy"
					value={`${snapshot().telemetry.energy.toFixed(1)} J/m²`}
				/>
				<Datum
					label="Delamination-area proxy"
					value={`${snapshot().telemetry.area.toFixed(2)} mm²`}
				/>
				<Datum
					label="Illustrative margin"
					tone={marginTone()}
					value={`${snapshot().telemetry.margin >= 0 ? "+" : ""}${snapshot().telemetry.margin.toFixed(2)}`}
				/>
			</div>
		</section>
	);
}
function Datum(props: { label: string; tone?: string; value: string }) {
	return (
		<div>
			<span>{props.label}</span>
			<b class={props.tone}>{props.value}</b>
		</div>
	);
}

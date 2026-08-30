import type { Accessor } from "solid-js";

import type {
	SimulationInput,
	SimulationSnapshot,
	SolverKind,
} from "../simulation";

type Props = {
	inputs: Accessor<SimulationInput>;
	snapshot: Accessor<SimulationSnapshot>;
	onInput: (value: Partial<SimulationInput>) => void;
	onRun: (solver: SolverKind) => void;
};

export function ControlPanel(props: Props) {
	const disabled = () => props.snapshot().status === "running";
	const range =
		(key: "thermalGradient" | "mechanicalLoad" | "coatingStrength") =>
		(event: InputEvent & { currentTarget: HTMLInputElement }) =>
			props.onInput({ [key]: Number(event.currentTarget.value) });

	return (
		<aside class="control-panel" aria-label="Simulation controls">
			<section>
				<h2>Microstructural and loading bounds</h2>
				<label for="architecture">Matrix architecture</label>
				<select
					id="architecture"
					onChange={(event) =>
						props.onInput({
							architecture: event.currentTarget
								.value as SimulationInput["architecture"],
						})
					}
					value={props.inputs().architecture}
				>
					<option value="sic_sic">SiC/SiC continuous-fibre composite</option>
					<option value="c_sic">C/SiC high-thermal composite</option>
					<option value="layered_tufroc">Layered fibrous insulation</option>
				</select>
				<Range
					label="Thermal gradient"
					max={250}
					min={20}
					onInput={range("thermalGradient")}
					unit="°C/mm"
					value={props.inputs().thermalGradient}
				/>
				<Range
					label="Aerodynamic shear load"
					max={100}
					min={5}
					onInput={range("mechanicalLoad")}
					unit="kN"
					value={props.inputs().mechanicalLoad}
				/>
				<Range
					label="Fibre coating shear limit"
					max={150}
					min={10}
					onInput={range("coatingStrength")}
					unit="MPa"
					value={props.inputs().coatingStrength}
				/>
			</section>
			<section>
				<h2>Comparison run</h2>
				<p>
					Illustrative UI state only. Wire it to declared reference evidence and
					a bounded surrogate before calling it adjudication.
				</p>
				<div class="btn-group">
					<button
						class="reference"
						disabled={disabled()}
						onClick={() => props.onRun("FEA")}
						type="button"
					>
						Run reference solver
					</button>
					<button
						class="surrogate"
						disabled={disabled()}
						onClick={() => props.onRun("FNO")}
						type="button"
					>
						Run surrogate
					</button>
				</div>
			</section>
			<section class="performance">
				<h2>Illustrative compute overhead</h2>
				<Metric
					label="Reference solver"
					seconds={props.snapshot().runs.FEA}
					tone="danger"
				/>
				<Metric
					label="Neural-operator surrogate"
					seconds={props.snapshot().runs.FNO}
					tone="success"
				/>
			</section>
		</aside>
	);
}

function Range(props: {
	label: string;
	max: number;
	min: number;
	onInput: (event: InputEvent & { currentTarget: HTMLInputElement }) => void;
	unit: string;
	value: number;
}) {
	const id = props.label.replaceAll(" ", "-");
	return (
		<div class="field">
			<label for={id}>
				{props.label}: <b>{props.value}</b> {props.unit}
			</label>
			<input
				id={id}
				max={props.max}
				min={props.min}
				onInput={props.onInput}
				step={5}
				type="range"
				value={props.value}
			/>
		</div>
	);
}

function Metric(props: {
	label: string;
	seconds: number | undefined;
	tone: "danger" | "success";
}) {
	return (
		<div class="metric">
			<span>{props.label}</span>
			<b class={props.tone}>
				{props.seconds === undefined ? "—" : `${props.seconds.toFixed(3)} s`}
			</b>
		</div>
	);
}

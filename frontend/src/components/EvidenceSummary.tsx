import { createEffect, createSignal, For, onCleanup, Show } from "solid-js";

export type EvidenceDetail = { label: string; value: string };

export type EvidenceSummaryProps = {
	phase: string;
	state: "running" | "completed" | "failed" | "cancelled";
	headline: string;
	containerObservedAt?: string;
	solverEvidenceAt?: string;
	residuals?: number[];
	details: EvidenceDetail[];
	terminal?: boolean;
};

export function EvidenceSummary(props: EvidenceSummaryProps) {
	const [expanded, setExpanded] = createSignal(false);
	let canvas: HTMLCanvasElement | undefined;

	createEffect(() => {
		const samples = props.residuals ?? [];
		if (!canvas || samples.length < 2) return;
		const context = canvas.getContext("2d");
		if (!context) return;
		const width = canvas.width;
		const height = canvas.height;
		const values = samples.map((sample) =>
			Math.log10(Math.max(sample, Number.MIN_VALUE)),
		);
		const minimum = Math.min(...values);
		const maximum = Math.max(...values);
		context.clearRect(0, 0, width, height);
		context.beginPath();
		context.strokeStyle = props.state === "failed" ? "#b42318" : "#266f5a";
		values.forEach((value, index) => {
			const x = (index / (values.length - 1)) * width;
			const y =
				maximum === minimum
					? height / 2
					: ((maximum - value) / (maximum - minimum)) * height;
			if (index === 0) context.moveTo(x, y);
			else context.lineTo(x, y);
		});
		context.stroke();
	});
	onCleanup(() => {
		canvas = undefined;
	});

	const copy = async () => {
		if (!props.terminal) return;
		await navigator.clipboard?.writeText(
			props.details
				.map((detail) => `${detail.label}: ${detail.value}`)
				.join("\n"),
		);
	};

	return (
		<section
			class="evidence-summary"
			aria-label={`${props.phase} evidence summary`}
		>
			<button
				aria-controls={`${props.phase}-detail`}
				aria-expanded={expanded()}
				class="evidence-summary-toggle"
				onClick={() => setExpanded(!expanded())}
				type="button"
			>
				<span aria-hidden="true">{expanded() ? "−" : "+"}</span>
				<span class="evidence-summary-heartbeat">
					<canvas height="18" ref={canvas} width="52" />
				</span>
				<span class="evidence-summary-state">
					<strong>{props.phase}</strong> · {props.headline}
				</span>
				<span class={`evidence-summary-anchor ${props.state}`}>
					{props.state}
				</span>
			</button>
			<p class="evidence-summary-facts">
				container observed: {props.containerObservedAt ?? "unavailable"} ·
				solver evidence: {props.solverEvidenceAt ?? "unavailable"}
			</p>
			<Show when={expanded()}>
				<div class="evidence-summary-detail" id={`${props.phase}-detail`}>
					<For each={props.details.slice(0, 5)}>
						{(detail) => (
							<div>
								<span>{detail.label}</span>
								<strong>{detail.value}</strong>
							</div>
						)}
					</For>
					<Show when={props.terminal}>
						<button
							class="evidence-summary-copy"
							onClick={() => void copy()}
							type="button"
						>
							Copy complete evidence
						</button>
					</Show>
				</div>
			</Show>
		</section>
	);
}

import { createTable, tableFeatures } from "@tanstack/solid-table";
import { createVirtualizer } from "@tanstack/solid-virtual";
import { createEffect, createSignal, For, onCleanup, Show } from "solid-js";

export type EvidenceDetail = {
	label: string;
	value: string;
	sequence?: number;
};

export type EvidenceSummaryProps = {
	phase: string;
	state: "pending" | "running" | "completed" | "failed" | "cancelled";
	headline: string;
	containerObservedAt?: string;
	solverEvidenceAt?: string;
	residuals?: number[];
	details: EvidenceDetail[];
	onExpand?: () => Promise<void>;
	loadOlder?: () => Promise<void>;
	hasOlder?: boolean;
	terminal?: boolean;
};

const features = tableFeatures({});

export function EvidenceSummary(props: EvidenceSummaryProps) {
	const [expanded, setExpanded] = createSignal(false);
	const [loading, setLoading] = createSignal(false);
	let canvas: HTMLCanvasElement | undefined;
	let scrollElement: HTMLDivElement | undefined;
	const table = createTable({
		features,
		columns: [
			{ accessorKey: "label", header: "Evidence" },
			{ accessorKey: "value", header: "Observed value" },
		],
		get data() {
			return props.details;
		},
	});
	const rows = () => table.getRowModel().rows;
	const virtualizer = createVirtualizer({
		get count() {
			return rows().length;
		},
		getScrollElement: () => scrollElement ?? null,
		estimateSize: () => 32,
		getItemKey: (index) => rows()[index].id,
		overscan: 4,
	});
	const renderedItems = () => {
		const items = virtualizer.getVirtualItems();
		return items.length > 0
			? items
			: rows()
					.slice(0, 5)
					.map((row, index) => ({ index, key: row.id, start: index * 32 }));
	};

	createEffect(() => {
		const samples = props.residuals ?? [];
		if (!canvas || samples.length < 2) return;
		const target = canvas;
		if (!target) return;
		const context = target.getContext("2d");
		if (!context) return;
		const values = samples.map((sample) =>
			Math.log10(Math.max(sample, Number.MIN_VALUE)),
		);
		const minimum = Math.min(...values);
		const maximum = Math.max(...values);
		context.clearRect(0, 0, target.width, target.height);
		context.beginPath();
		context.strokeStyle = props.state === "failed" ? "#b42318" : "#266f5a";
		values.forEach((value, index) => {
			const x = (index / (values.length - 1)) * target.width;
			const y =
				maximum === minimum
					? target.height / 2
					: ((maximum - value) / (maximum - minimum)) * target.height;
			if (index === 0) context.moveTo(x, y);
			else context.lineTo(x, y);
		});
		context.stroke();
	});
	onCleanup(() => {
		canvas = undefined;
	});

	const loadOlder = async () => {
		if (!props.loadOlder || loading()) return;
		setLoading(true);
		try {
			await props.loadOlder();
		} finally {
			setLoading(false);
		}
	};
	const copy = async () => {
		if (!props.terminal) return;
		await navigator.clipboard?.writeText(
			props.details
				.map((detail) => `${detail.label}: ${detail.value}`)
				.join("\n"),
		);
	};
	const toggle = () => {
		const next = !expanded();
		setExpanded(next);
		if (next && props.details.length === 0 && props.onExpand)
			void props.onExpand();
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
				onClick={toggle}
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
					<div
						class="evidence-summary-table"
						ref={scrollElement}
						style={{ height: "160px", overflow: "auto" }}
					>
						<div
							style={{
								height: `${virtualizer.getTotalSize()}px`,
								position: "relative",
							}}
						>
							<For each={renderedItems()}>
								{(item) => {
									const row = () => rows()[item.index];
									return (
										<div
											class="evidence-summary-row"
											data-index={item.index}
											ref={(node) => virtualizer.measureElement(node)}
											style={{
												position: "absolute",
												transform: `translateY(${item.start}px)`,
												width: "100%",
											}}
										>
											<span>{row().original.label}</span>
											<strong>{row().original.value}</strong>
										</div>
									);
								}}
							</For>
						</div>
					</div>
					<Show when={props.hasOlder}>
						<button
							class="evidence-summary-copy"
							disabled={loading()}
							onClick={() => void loadOlder()}
							type="button"
						>
							{loading() ? "Loading…" : "Load older evidence"}
						</button>
					</Show>
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

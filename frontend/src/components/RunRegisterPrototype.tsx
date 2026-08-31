/** PROTOTYPE ONLY — three register layouts, switchable at /?variant=. */
import { useNavigate } from "@tanstack/solid-router";
import { createSignal, For, onCleanup, onMount, Show } from "solid-js";

import {
	fixtureRunRegister,
	prototypeVariants,
	type RegisterEntry,
	type RegisterVariant,
} from "../prototypes/run-register";

type Props = { variant: RegisterVariant };

const entries = fixtureRunRegister.read();

export function RunRegisterPrototype(props: Props) {
	const [selectedId, setSelectedId] = createSignal("run-042");
	const selected = () => entries.find((entry) => entry.runId === selectedId()) ?? entries[0];
	return (
		<main class={`register-prototype variant-${props.variant}`}>
			<PrototypeMasthead />
			<Show when={props.variant === "paintbox"}>
				<PaintboxVariant entries={entries} selected={selected} select={setSelectedId} />
			</Show>
			<Show when={props.variant === "ledger"}>
				<LedgerVariant entries={entries} selected={selected} select={setSelectedId} />
			</Show>
			<Show when={props.variant === "sequence"}>
				<SequenceVariant entries={entries} selected={selected} select={setSelectedId} />
			</Show>
			<Show when={import.meta.env.DEV}>
				<PrototypeSwitcher variant={props.variant} />
			</Show>
		</main>
	);
}

function PrototypeMasthead() {
	return (
		<header class="register-masthead">
			<div>
				<p class="eyebrow">CMC Pipeline · browser prototype</p>
				<h1>RUN REGISTER</h1>
			</div>
			<p class="fixture-stamp">ILLUSTRATIVE FIXTURE · NOT LIVE EXECUTION</p>
		</header>
	);
}

function PaintboxVariant(props: VariantProps) {
	return (
		<section class="paintbox-layout" aria-label="Paintbox grid register prototype">
			<div class="paintbox-register">
				<p class="section-label">Five observed attempts</p>
				<div class="paintbox-rows">
					<For each={props.entries}>
						{(entry) => <PaintboxRow entry={entry} selected={props.selected().runId === entry.runId} select={props.select} />}
					</For>
				</div>
			</div>
			<RunDetail entry={props.selected()} />
		</section>
	);
}

function PaintboxRow(props: { entry: RegisterEntry; selected: boolean; select: (id: string) => void }) {
	return (
		<button
			aria-pressed={props.selected}
			class={`paintbox-row attention-${props.entry.attention} ${props.selected ? "is-selected" : ""}`}
			onClick={() => props.select(props.entry.runId)}
			type="button"
		>
			<span class="paintbox-tile" />
			<span class="paintbox-row-copy"><b>{props.entry.runId}</b><small>{props.entry.phase.name}</small></span>
			<span class="paintbox-row-status">{statusLabel(props.entry)}</span>
			<span class="paintbox-row-freshness">{props.entry.freshness.observedAt}</span>
		</button>
	);
}

function LedgerVariant(props: VariantProps) {
	return (
		<section class="ledger-layout" aria-label="Editorial ledger register prototype">
			<div class="ledger-sidebar">
				<p class="section-label">Register / all attempts</p>
				<h2>What the runner last confirmed.</h2>
				<p>Counts and freshness are evidence. Completion remains a declared outcome.</p>
				<div class="ledger-key"><span class="legend-running" />running <span class="legend-attention" />attention <span class="legend-stale" />stale</div>
			</div>
			<div class="ledger-table-wrap">
				<table class="ledger-table">
					<thead><tr><th>Run</th><th>Phase</th><th>Evidence</th><th>State</th><th>Observed</th></tr></thead>
					<tbody><For each={props.entries}>{(entry) => <tr class={props.selected().runId === entry.runId ? "is-selected" : ""} onClick={() => props.select(entry.runId)}><td><b>{entry.runId}</b><small>{entry.caseId}</small></td><td>{entry.phase.name}</td><td>{evidenceLabel(entry)}</td><td><StatusMark entry={entry} /></td><td>{entry.freshness.observedAt}</td></tr>}</For></tbody>
				</table>
				<RunDetail entry={props.selected()} compact />
			</div>
		</section>
	);
}

function SequenceVariant(props: VariantProps) {
	return (
		<section class="sequence-layout" aria-label="Execution sequence register prototype">
			<aside class="sequence-register">
				<p class="section-label">Select an execution</p>
				<For each={props.entries}>{(entry) => <button aria-pressed={props.selected().runId === entry.runId} class={props.selected().runId === entry.runId ? "is-selected" : ""} onClick={() => props.select(entry.runId)} type="button"><StatusMark entry={entry} /><span><b>{entry.runId}</b><small>{entry.phase.name}</small></span></button>}</For>
			</aside>
			<div class="sequence-detail"><RunDetail entry={props.selected()} sequence /></div>
		</section>
	);
}

function RunDetail(props: { compact?: boolean; entry: RegisterEntry; sequence?: boolean }) {
	const detail = () => fixtureRunRegister.inspect(props.entry.runId);
	return (
		<aside class={`run-detail ${props.compact ? "is-compact" : ""}`} aria-live="polite">
			<p class="section-label">Selected run</p>
			<h2>{props.entry.runId}</h2>
			<p class="detail-phase">{props.entry.phase.name}</p>
			<div class="detail-state"><StatusMark entry={props.entry} /><span>{statusLabel(props.entry)}</span></div>
			<Show when={detail()}>{(record) => <>
				<div class={`phase-map ${props.sequence ? "is-sequence" : ""}`} aria-label="Declared phase map"><For each={record().phaseMap}>{(state) => <span class={`phase-${state}`} />}</For></div>
				<p class="detail-note">{record().note}</p>
				<section><h3>Evidence</h3><ul><For each={record().evidence}>{(item) => <li>{item}</li>}</For></ul></section>
				<section><h3>Provenance</h3><p>{record().claimBoundary}</p></section>
				<section><h3>Latest artifact</h3><code>{record().latestArtifact}</code></section>
			</>}</Show>
		</aside>
	);
}

function StatusMark(props: { entry: RegisterEntry }) { return <span aria-hidden="true" class={`status-mark attention-${props.entry.attention}`} />; }

function PrototypeSwitcher(props: { variant: RegisterVariant }) {
	const navigate = useNavigate({ from: "/" });
	const change = (delta: number) => {
		const index = prototypeVariants.findIndex((variant) => variant.key === props.variant);
		const next = prototypeVariants[(index + delta + prototypeVariants.length) % prototypeVariants.length];
		void navigate({ replace: true, search: { variant: next.key } });
	};
	onMount(() => {
		const onKeyDown = (event: KeyboardEvent) => {
			const element = event.target as HTMLElement | null;
			if (element?.matches("input, textarea, [contenteditable='true']")) return;
			if (event.key === "ArrowLeft") change(-1);
			if (event.key === "ArrowRight") change(1);
		};
		window.addEventListener("keydown", onKeyDown);
		onCleanup(() => window.removeEventListener("keydown", onKeyDown));
	});
	return <nav class="prototype-switcher" aria-label="Prototype variants"><button onClick={() => change(-1)} type="button">←</button><span>{prototypeVariants.find((variant) => variant.key === props.variant)?.name}</span><button onClick={() => change(1)} type="button">→</button></nav>;
}

type VariantProps = { entries: readonly RegisterEntry[]; selected: () => RegisterEntry; select: (id: string) => void };

function evidenceLabel(entry: RegisterEntry) {
	return entry.evidence.accepted === undefined ? `${entry.evidence.fixedCompleted} / ${entry.evidence.fixedTotal} declared` : `${entry.evidence.accepted} / ${entry.evidence.attempted} accepted`;
}

function statusLabel(entry: RegisterEntry) {
	if (entry.outcome) return entry.outcome;
	return entry.attention === "normal" ? entry.lifecycle : entry.attention;
}

import { Shape, ShapeStream } from "@electric-sql/client";
import { createEffect, createSignal, For, onCleanup, Show } from "solid-js";

import { type EvidenceDetail, EvidenceSummary } from "./EvidenceSummary";

type RunSummary = {
	run_id: string;
	revision: number;
	lifecycle: string;
	outcome?: string | null;
	current_phase_key?: string | null;
	state?: "running" | "completed" | "failed" | "cancelled" | null;
	headline: Record<string, unknown>;
	trend: { kind?: string; samples?: number[] };
	container_observed_at?: string | null;
	solver_evidence_at?: string | null;
};
type DetailResponse = {
	details: Array<{
		sequence: number;
		label: string;
		value: string;
	}>;
	next_before_sequence: number | null;
};
type ElectricRunRow = {
	run_id: string;
	revision: string;
	lifecycle: string;
	outcome: string | null;
	evidence_disposition: string | null;
	current_phase_key: string | null;
};
type ElectricPhaseRow = {
	run_id: string;
	phase_key: string;
	state: RunSummary["state"];
	headline: Record<string, unknown>;
	trend: RunSummary["trend"];
	warnings: string[];
	last_container_observed_at: string | null;
	last_solver_evidence_at: string | null;
};

const phaseLabels: Record<string, string> = {
	queued: "Queued",
	admitted: "Admitted",
	mesh: "Mesh",
	verify: "Verify",
	solve: "Solve",
	adjudicate: "Adjudicate",
	publish: "Publish",
};
const phases = ["admitted", "mesh", "verify", "adjudicate", "publish"];

function detailText(item: DetailResponse["details"][number]): EvidenceDetail {
	return {
		sequence: item.sequence,
		label: item.label,
		value: item.value,
	};
}

export function V3RunRegister() {
	const [runs, setRuns] = createSignal<RunSummary[]>([]);
	const [details, setDetails] = createSignal<Record<string, EvidenceDetail[]>>(
		{},
	);
	const [before, setBefore] = createSignal<Record<string, number | null>>({});
	const [error, setError] = createSignal<string | null>(null);
	const [registerSequence, setRegisterSequence] = createSignal(0);
	const [snapshotReady, setSnapshotReady] = createSignal(false);
	const snapshot = async () => {
		const response = await fetch("/api/v3/runs");
		if (!response.ok) throw new Error("Run register snapshot unavailable.");
		const payload = (await response.json()) as {
			runs: RunSummary[];
			register_sequence?: number;
		};
		setRuns(payload.runs);
		if (payload.register_sequence !== undefined)
			setRegisterSequence(payload.register_sequence);
		setSnapshotReady(true);
	};
	createEffect(() => {
		void snapshot().catch((cause: unknown) =>
			setError(
				cause instanceof Error ? cause.message : "Run register unavailable.",
			),
		);
	});
	createEffect(() => {
		const aborter = new AbortController();
		const runShape = new Shape(
			new ShapeStream<ElectricRunRow>({
				url: "/electric/v1/shape",
				params: { table: "run_summary_projections" },
				liveSse: true,
				signal: aborter.signal,
			}),
		);
		const phaseShape = new Shape(
			new ShapeStream<ElectricPhaseRow>({
				url: "/electric/v1/shape",
				params: { table: "run_phase_summary_projections" },
				liveSse: true,
				signal: aborter.signal,
			}),
		);
		const project = () => {
			const phaseByRun = new Map(
				phaseShape.currentRows.map(
					(phase) => [`${phase.run_id}:${phase.phase_key}`, phase] as const,
				),
			);
			setRuns(
				runShape.currentRows.map((run) => {
					const phase = run.current_phase_key
						? phaseByRun.get(`${run.run_id}:${run.current_phase_key}`)
						: undefined;
					return {
						run_id: run.run_id,
						revision: Number(run.revision),
						lifecycle: run.lifecycle,
						outcome: run.outcome,
						current_phase_key: run.current_phase_key,
						state: phase?.state,
						headline: phase?.headline ?? {},
						trend: phase?.trend ?? {},
						container_observed_at: phase?.last_container_observed_at,
						solver_evidence_at: phase?.last_solver_evidence_at,
					};
				}),
			);
		};
		const unsubscribeRuns = runShape.subscribe(project);
		const unsubscribePhases = phaseShape.subscribe(project);
		void Promise.all([runShape.rows, phaseShape.rows])
			.then(project)
			.catch(() => setError("Electric run projection unavailable."));
		onCleanup(() => {
			unsubscribeRuns();
			unsubscribePhases();
			aborter.abort();
		});
	});
	createEffect(() => {
		if (!snapshotReady()) return;
		const stream = new EventSource(
			`/api/v3/events?after_sequence=${registerSequence()}`,
		);
		stream.addEventListener("revision", (event) => {
			const notice = JSON.parse((event as MessageEvent).data) as {
				register_sequence: number;
			};
			setRegisterSequence((sequence) =>
				Math.max(sequence, notice.register_sequence),
			);
			// Electric Shapes own row state; SSE is only a compact resume notice.
		});
		onCleanup(() => stream.close());
	});
	const loadDetails = async (run: RunSummary) => {
		const phase = run.current_phase_key ?? "admitted";
		const key = `${run.run_id}:${phase}`;
		const query =
			before()[key] === undefined
				? ""
				: `&before_sequence=${before()[key] ?? ""}`;
		const response = await fetch(
			`/api/v3/runs/${run.run_id}/details?phase=${phase}&limit=5${query}`,
		);
		if (!response.ok) throw new Error("Evidence detail unavailable.");
		const payload = (await response.json()) as DetailResponse;
		setDetails((existing) => ({
			...existing,
			[key]: [...(existing[key] ?? []), ...payload.details.map(detailText)],
		}));
		setBefore((existing) => ({
			...existing,
			[key]: payload.next_before_sequence,
		}));
	};

	return (
		<section class="v3-run-register" aria-label="V3 operational run register">
			<header>
				<p class="eyebrow">CMC Pipeline · V3 local-development projection</p>
				<h2>Operational run ribbon</h2>
				<p>
					Bounded evidence projection. It shows observed lifecycle facts, not a
					predicted completion time.
				</p>
			</header>
			<Show when={error()}>{(message) => <output>{message()}</output>}</Show>
			<Show when={runs().length === 0 && !error()}>
				<output>No V3 run summaries available.</output>
			</Show>
			<For each={runs()}>
				{(run) => {
					const phase = () => run.current_phase_key ?? "queued";
					const key = () => `${run.run_id}:${phase()}`;
					return (
						<article aria-label={`Run ${run.run_id}`}>
							<ol class="run-ribbon" aria-label="Run phases">
								<For each={phases}>
									{(phaseKey) => (
										<li
											class={`run-ribbon-phase ${phaseKey === phase() ? (run.state ?? "pending") : "pending"}`}
										>
											{phaseLabels[phaseKey]}
										</li>
									)}
								</For>
							</ol>
							<EvidenceSummary
								phase={phaseLabels[phase()] ?? phase()}
								state={run.state ?? "pending"}
								headline={
									Object.values(run.headline).join(" · ") || run.lifecycle
								}
								containerObservedAt={run.container_observed_at ?? undefined}
								solverEvidenceAt={run.solver_evidence_at ?? undefined}
								residuals={
									run.trend.kind === "log-residual"
										? run.trend.samples
										: undefined
								}
								details={details()[key()] ?? []}
								hasOlder={before()[key()] != null}
								onExpand={() => loadDetails(run)}
								loadOlder={() => loadDetails(run)}
								terminal={run.lifecycle === "terminal"}
							/>
							<a
								href={`${import.meta.env.VITE_PHYSICS_APP_ORIGIN ?? "http://127.0.0.1:3002"}/runs/${encodeURIComponent(run.run_id)}`}
							>
								View physics result
							</a>
						</article>
					);
				}}
			</For>
		</section>
	);
}

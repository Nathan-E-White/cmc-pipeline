/**
 * PROTOTYPE ONLY — fixture RunRegister for the browser register experiment.
 *
 * Question: which register layout makes backend activity easiest to scan
 * without making a claim that this data came from a live solver?
 */

export type RegisterVariant = "paintbox" | "ledger" | "sequence";

export type Attention = "normal" | "cutback" | "stale" | "needs-review" | "failed";
export type Lifecycle =
	| "submitted"
	| "admitted"
	| "running"
	| "cancel-requested"
	| "terminal";
export type Outcome = "solved" | "failed" | "cancelled" | "indeterminate";

export type RegisterEntry = {
	attention: Attention;
	caseId: string;
	evidence: { accepted?: number; attempted?: number; fixedCompleted?: number; fixedTotal?: number };
	freshness: { observedAt: string; source: "fixture" };
	lifecycle: Lifecycle;
	outcome?: Outcome;
	phase: { name: string; state: "pending" | "active" | "complete" | "blocked" };
	runId: string;
};

export type RunDetail = {
	claimBoundary: string;
	evidence: string[];
	latestArtifact: string;
	note: string;
	phaseMap: Array<"complete" | "active" | "blocked" | "pending">;
};

export interface RunRegister {
	inspect(runId: string): RunDetail | undefined;
	read(): readonly RegisterEntry[];
}

const entries: RegisterEntry[] = [
	{
		attention: "cutback",
		caseId: "edge-cracked-plate-reversible-v2",
		evidence: { accepted: 7, attempted: 11 },
		freshness: { observedAt: "14 seconds ago", source: "fixture" },
		lifecycle: "running",
		phase: { name: "fine solve", state: "active" },
		runId: "run-042",
	},
	{
		attention: "normal",
		caseId: "edge-cracked-plate-reversible-v2",
		evidence: { fixedCompleted: 2, fixedTotal: 3 },
		freshness: { observedAt: "4 seconds ago", source: "fixture" },
		lifecycle: "running",
		phase: { name: "medium audit", state: "complete" },
		runId: "run-043",
	},
	{
		attention: "needs-review",
		caseId: "edge-cracked-plate-bridged-v2",
		evidence: { fixedCompleted: 3, fixedTotal: 3 },
		freshness: { observedAt: "2 minutes ago", source: "fixture" },
		lifecycle: "terminal",
		outcome: "indeterminate",
		phase: { name: "convergence adjudication", state: "blocked" },
		runId: "run-044",
	},
	{
		attention: "stale",
		caseId: "edge-cracked-plate-v1",
		evidence: { fixedCompleted: 1, fixedTotal: 3 },
		freshness: { observedAt: "3 minutes ago", source: "fixture" },
		lifecycle: "running",
		phase: { name: "coarse mesh audit", state: "active" },
		runId: "run-045",
	},
	{
		attention: "normal",
		caseId: "edge-cracked-plate-v1",
		evidence: { fixedCompleted: 3, fixedTotal: 3 },
		freshness: { observedAt: "8 minutes ago", source: "fixture" },
		lifecycle: "terminal",
		outcome: "solved",
		phase: { name: "artifact published", state: "complete" },
		runId: "run-046",
	},
];

const details: Record<string, RunDetail> = {
	"run-042": {
		claimBoundary: "Synthetic reversible-cohesive numerical tracer; no toughness or fracture-energy authority.",
		evidence: ["7 accepted / 11 attempted", "2 cutbacks recorded", "relative residual 2e-9"],
		latestArtifact: "levels/fine/reversible-cohesive-program.json",
		note: "Working through a numerical difficulty; no completion percentage is asserted.",
		phaseMap: ["complete", "complete", "active", "pending", "pending", "pending"],
	},
	"run-043": {
		claimBoundary: "Fixture projection only; no solver execution is implied.",
		evidence: ["2 mesh levels audited", "one declared level remains", "source: fixture"],
		latestArtifact: "levels/medium/mesh-audit.json",
		note: "Fixed work is shown as a count because the denominator is declared.",
		phaseMap: ["complete", "complete", "active", "pending", "pending", "pending"],
	},
	"run-044": {
		claimBoundary: "A completed process is not automatically a solved numerical result.",
		evidence: ["fine/medium comparison unavailable", "adjudication needs review", "result remains indeterminate"],
		latestArtifact: "provenance-convergence.json",
		note: "The register preserves the distinction between a terminal run and a justified outcome.",
		phaseMap: ["complete", "complete", "complete", "blocked", "pending", "pending"],
	},
	"run-045": {
		claimBoundary: "Freshness is a display fact, not evidence of a healthy worker.",
		evidence: ["last observed 3 minutes ago", "no terminal event received", "awaiting reconciliation"],
		latestArtifact: "levels/coarse/mesh-audit.json",
		note: "Stale is intentionally distinct from failed.",
		phaseMap: ["active", "pending", "pending", "pending", "pending", "pending"],
	},
	"run-046": {
		claimBoundary: "Fixed numerical benchmark values, not physical validation or qualification.",
		evidence: ["three mesh levels complete", "declared gate satisfied", "artifact published"],
		latestArtifact: "provenance-convergence.json",
		note: "Solved describes the declared computation only.",
		phaseMap: ["complete", "complete", "complete", "complete", "complete", "complete"],
	},
};

export const fixtureRunRegister: RunRegister = {
	inspect: (runId) => details[runId],
	read: () => entries,
};

export const prototypeVariants: Array<{ key: RegisterVariant; name: string }> = [
	{ key: "paintbox", name: "Paintbox grid" },
	{ key: "ledger", name: "Editorial ledger" },
	{ key: "sequence", name: "Execution sequence" },
];

export type Architecture = "sic_sic" | "c_sic" | "layered_tufroc";
export type SolverKind = "FEA" | "FNO";

export type SimulationInput = {
	architecture: Architecture;
	coatingStrength: number;
	mechanicalLoad: number;
	thermalGradient: number;
};

export type SimulationSnapshot = {
	mode: string;
	progress: number;
	runs: Record<SolverKind, number | undefined>;
	status: "idle" | "running" | "complete";
	telemetry: { area: number; energy: number; margin: number; nodes: string };
	title: string;
};

export const defaultInputs: SimulationInput = {
	architecture: "sic_sic",
	coatingStrength: 60,
	mechanicalLoad: 45,
	thermalGradient: 120,
};

export function nodeCountFor(architecture: Architecture) {
	return { c_sic: "895,000", layered_tufroc: "310,000", sic_sic: "640,000" }[
		architecture
	];
}

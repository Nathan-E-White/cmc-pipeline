export type FixtureInputs = {
	coatingShearLimitMpa: number;
	mechanicalLoadKn: number;
	thermalGradientCPerMm: number;
};

export type ReferenceRunSubmission = {
	caseId: string;
	inputs: FixtureInputs;
};

export type ReferenceRun = {
	runId: string;
	caseId: string;
	status: "queued" | "running" | "complete" | "failed";
};

export type FixtureDescriptor = {
	corpusId: string;
	kind: "representative";
};

export type FixtureProvenance = {
	sourceKind: "fixture";
};

export type ReferenceRunSubmissionResponse = {
	fixture: FixtureDescriptor;
	provenance: FixtureProvenance;
	run: ReferenceRun;
};

export type ReferenceRunResult = {
	quantity: string;
	value: number;
	units: string;
};

export type ReferenceRunResultResponse = {
	fixture: FixtureDescriptor;
	provenance: FixtureProvenance;
	result: ReferenceRunResult;
};

export type SurrogateObservation = {
	quantity: string;
	value: number;
	units: string;
	domainStatus?: "outside_declared_domain";
};

export type FixtureVerification = {
	verificationId: string;
	status: "accepted" | "rejected" | "indeterminate";
	quantity: string;
	referenceValue: number;
	surrogateValue: number;
	relativeError: number | null;
	units: string;
};

export type FixtureVerificationResponse = {
	fixture: FixtureDescriptor;
	provenance: FixtureProvenance & { claimBoundary: string };
	verification: FixtureVerification;
};

export type HttpRequest = {
	method: "GET" | "POST";
	path: string;
	body: unknown;
};

export type HttpResponse = {
	status: number;
	body: unknown;
};

export type HttpTransport = {
	request: (request: HttpRequest) => Promise<HttpResponse>;
};

export type SimulationClient = {
	submitReferenceRun: (
		submission: ReferenceRunSubmission,
	) => Promise<ReferenceRunSubmissionResponse>;
	getReferenceRun: (runId: string) => Promise<ReferenceRunSubmissionResponse>;
	getReferenceRunResult: (runId: string) => Promise<ReferenceRunResultResponse>;
	verifySurrogateObservation: (
		referenceRunId: string,
		submission: ReferenceRunSubmission,
		observation: SurrogateObservation,
	) => Promise<FixtureVerificationResponse>;
};

export class SimulationApiError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "SimulationApiError";
	}
}

export function createSimulationClient(
	transport: HttpTransport,
): SimulationClient {
	return {
		submitReferenceRun: async (
			submission: ReferenceRunSubmission,
		): Promise<ReferenceRunSubmissionResponse> => {
			const response = await transport.request({
				method: "POST",
				path: "/api/v1/reference-runs",
				body: {
					case_id: submission.caseId,
					inputs: {
						coating_shear_limit_mpa: submission.inputs.coatingShearLimitMpa,
						mechanical_load_kn: submission.inputs.mechanicalLoadKn,
						thermal_gradient_c_per_mm: submission.inputs.thermalGradientCPerMm,
					},
				},
			});
			if (response.status !== 202) {
				throw new SimulationApiError(
					"Fixture reference-run submission was not accepted.",
				);
			}
			return parseReferenceRun(response.body, ["queued"]);
		},
		getReferenceRun: async (runId) => {
			const response = await transport.request({
				method: "GET",
				path: `/api/v1/reference-runs/${runId}`,
				body: undefined,
			});
			if (response.status !== 200) {
				throw new SimulationApiError(
					"Fixture reference-run status was unavailable.",
				);
			}
			return parseReferenceRun(response.body, [
				"queued",
				"running",
				"complete",
				"failed",
			]);
		},
		getReferenceRunResult: async (runId) => {
			const response = await transport.request({
				method: "GET",
				path: `/api/v1/reference-runs/${runId}/results`,
				body: undefined,
			});
			if (response.status !== 200) {
				throw new SimulationApiError(
					"Fixture reference-run result was unavailable.",
				);
			}
			return parseReferenceRunResult(response.body);
		},
		verifySurrogateObservation: async (
			referenceRunId,
			submission,
			observation,
		) => {
			const response = await transport.request({
				method: "POST",
				path: "/api/v1/simulation/verify",
				body: {
					reference_run_id: referenceRunId,
					inputs: {
						coating_shear_limit_mpa: submission.inputs.coatingShearLimitMpa,
						mechanical_load_kn: submission.inputs.mechanicalLoadKn,
						thermal_gradient_c_per_mm: submission.inputs.thermalGradientCPerMm,
					},
					observation: {
						quantity: observation.quantity,
						value: observation.value,
						units: observation.units,
						...(observation.domainStatus
							? { domain_status: observation.domainStatus }
							: {}),
					},
				},
			});
			if (response.status !== 201) {
				throw new SimulationApiError(
					"Fixture surrogate comparison was unavailable.",
				);
			}
			return parseFixtureVerification(response.body);
		},
	};
}

function createFetchTransport(
	fetchImplementation: typeof fetch = fetch,
): HttpTransport {
	return {
		request: async ({ body, method, path }) => {
			const response = await fetchImplementation(path, {
				method,
				headers: {
					Accept: "application/json",
					"Content-Type": "application/json",
				},
				body: JSON.stringify(body),
			});
			return { status: response.status, body: await response.json() };
		},
	};
}

export const simulationClient = createSimulationClient(createFetchTransport());

function parseReferenceRun(
	body: unknown,
	allowedStatuses: ReferenceRun["status"][],
): ReferenceRunSubmissionResponse {
	if (
		!isRecord(body) ||
		body.api_version !== "v1" ||
		!isRecord(body.fixture) ||
		!isRecord(body.provenance) ||
		!isRecord(body.run)
	) {
		throw new SimulationApiError(
			"Fixture reference-run response was malformed.",
		);
	}
	const { corpus_id: corpusId, kind } = body.fixture;
	const { source_kind: sourceKind } = body.provenance;
	const { case_id: caseId, run_id: runId, status } = body.run;
	if (
		typeof corpusId !== "string" ||
		kind !== "representative" ||
		sourceKind !== "fixture" ||
		typeof caseId !== "string" ||
		typeof runId !== "string" ||
		!isReferenceRunStatus(status) ||
		!allowedStatuses.includes(status)
	) {
		throw new SimulationApiError(
			"Fixture reference-run response was malformed.",
		);
	}
	return {
		fixture: { corpusId, kind },
		provenance: { sourceKind },
		run: { caseId, runId, status },
	};
}

function parseReferenceRunResult(body: unknown): ReferenceRunResultResponse {
	if (
		!isRecord(body) ||
		body.api_version !== "v1" ||
		!isRecord(body.fixture) ||
		!isRecord(body.provenance) ||
		!isRecord(body.result)
	) {
		throw new SimulationApiError(
			"Fixture reference-run result response was malformed.",
		);
	}
	const { corpus_id: corpusId, kind } = body.fixture;
	const { source_kind: sourceKind } = body.provenance;
	const { quantity, units, value } = body.result;
	if (
		typeof corpusId !== "string" ||
		kind !== "representative" ||
		sourceKind !== "fixture" ||
		typeof quantity !== "string" ||
		typeof units !== "string" ||
		typeof value !== "number"
	) {
		throw new SimulationApiError(
			"Fixture reference-run result response was malformed.",
		);
	}
	return {
		fixture: { corpusId, kind },
		provenance: { sourceKind },
		result: { quantity, units, value },
	};
}

function parseFixtureVerification(body: unknown): FixtureVerificationResponse {
	if (
		!isRecord(body) ||
		body.api_version !== "v1" ||
		!isRecord(body.fixture) ||
		!isRecord(body.provenance) ||
		!isRecord(body.verification)
	) {
		throw new SimulationApiError(
			"Fixture verification response was malformed.",
		);
	}
	const { corpus_id: corpusId, kind } = body.fixture;
	const { claim_boundary: claimBoundary, source_kind: sourceKind } =
		body.provenance;
	const {
		quantity,
		reference_value: referenceValue,
		relative_error: relativeError,
		status,
		surrogate_value: surrogateValue,
		units,
		verification_id: verificationId,
	} = body.verification;
	if (
		typeof corpusId !== "string" ||
		kind !== "representative" ||
		sourceKind !== "fixture" ||
		typeof claimBoundary !== "string" ||
		typeof verificationId !== "string" ||
		!isVerificationStatus(status) ||
		typeof quantity !== "string" ||
		typeof referenceValue !== "number" ||
		typeof surrogateValue !== "number" ||
		(relativeError !== null && typeof relativeError !== "number") ||
		typeof units !== "string"
	) {
		throw new SimulationApiError(
			"Fixture verification response was malformed.",
		);
	}
	return {
		fixture: { corpusId, kind },
		provenance: { claimBoundary, sourceKind },
		verification: {
			quantity,
			referenceValue,
			relativeError,
			status,
			surrogateValue,
			units,
			verificationId,
		},
	};
}

function isReferenceRunStatus(value: unknown): value is ReferenceRun["status"] {
	return (
		value === "queued" ||
		value === "running" ||
		value === "complete" ||
		value === "failed"
	);
}

function isVerificationStatus(
	value: unknown,
): value is FixtureVerification["status"] {
	return (
		value === "accepted" || value === "rejected" || value === "indeterminate"
	);
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

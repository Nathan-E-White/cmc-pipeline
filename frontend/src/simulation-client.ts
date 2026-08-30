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
	status: "queued";
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

export type HttpRequest = {
	method: "POST";
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

export class SimulationApiError extends Error {
	constructor(message: string) {
		super(message);
		this.name = "SimulationApiError";
	}
}

export function createSimulationClient(transport: HttpTransport) {
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
			return parseReferenceRun(response.body);
		},
	};
}

export function createFetchTransport(
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

function parseReferenceRun(body: unknown): ReferenceRunSubmissionResponse {
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
		status !== "queued"
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

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

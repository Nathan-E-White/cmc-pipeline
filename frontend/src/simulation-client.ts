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
	caseId: string;
	kind: "representative";
	revision: string;
};

export type ReferenceSolutionProvenance = {
	discretizationId: string;
	modelId: string;
	solverConfigurationId: string;
};

export type SurrogateProvenance = {
	domainId: string;
	modelId: string;
};

export type FixtureProvenance = {
	claimBoundary: string;
	referenceSolution: ReferenceSolutionProvenance;
	sourceKind: "fixture";
	surrogate?: SurrogateProvenance;
};

export type FixtureCatalogProvenance = {
	claimBoundary: string;
	sourceKind: "fixture";
};

export type FixtureCaseSummary = {
	architecture: string;
	availability: {
		adjudication: "available" | "unavailable";
		mesh: "available" | "unavailable";
	};
	caseId: string;
	label: string;
};

export type FixtureCatalogResponse = {
	cases: FixtureCaseSummary[];
	fixture: { corpusId: string; kind: "representative" };
	provenance: FixtureCatalogProvenance;
};

export type FixtureCaseResponse = {
	case: { architecture: string; inputs: FixtureInputs; label: string };
	fixture: FixtureDescriptor;
	provenance: FixtureProvenance;
};

export type FixtureAdjudicationResponse = {
	adjudication: { quantity: string; surrogateValue: number; units: string };
	fixture: FixtureDescriptor;
	provenance: FixtureProvenance;
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
	provenance: FixtureProvenance;
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
	listFixtureCases: () => Promise<FixtureCatalogResponse>;
	getFixtureCase: (caseId: string) => Promise<FixtureCaseResponse>;
	getFixtureAdjudication: (
		caseId: string,
	) => Promise<FixtureAdjudicationResponse>;
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
		listFixtureCases: async (): Promise<FixtureCatalogResponse> => {
			const response = await transport.request({
				method: "GET",
				path: "/api/v1/cases",
				body: undefined,
			});
			if (response.status !== 200) {
				throw new SimulationApiError("Fixture case catalog was unavailable.");
			}
			return parseFixtureCatalog(response.body);
		},
		getFixtureCase: async (caseId): Promise<FixtureCaseResponse> => {
			const response = await transport.request({
				method: "GET",
				path: `/api/v1/cases/${caseId}`,
				body: undefined,
			});
			if (response.status !== 200) {
				throw new SimulationApiError("Fixture case detail was unavailable.");
			}
			return parseFixtureCase(response.body);
		},
		getFixtureAdjudication: async (
			caseId,
		): Promise<FixtureAdjudicationResponse> => {
			const response = await transport.request({
				method: "GET",
				path: `/api/v1/cases/${caseId}/adjudication`,
				body: undefined,
			});
			if (response.status !== 200)
				throw new SimulationApiError("Fixture adjudication was unavailable.");
			return parseFixtureAdjudication(response.body);
		},
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

function parseFixtureCatalog(body: unknown): FixtureCatalogResponse {
	if (
		!isRecord(body) ||
		body.api_version !== "v1" ||
		!isRecord(body.fixture) ||
		!isRecord(body.provenance) ||
		!Array.isArray(body.cases)
	) {
		throw new SimulationApiError("Fixture case catalog was malformed.");
	}
	const { corpus_id: corpusId, kind } = body.fixture;
	const { claim_boundary: claimBoundary, source_kind: sourceKind } =
		body.provenance;
	if (
		typeof corpusId !== "string" ||
		kind !== "representative" ||
		sourceKind !== "fixture" ||
		typeof claimBoundary !== "string"
	) {
		throw new SimulationApiError("Fixture case catalog was malformed.");
	}
	const cases = body.cases.map((entry) => {
		if (
			!isRecord(entry) ||
			!isRecord(entry.availability) ||
			typeof entry.case_id !== "string" ||
			typeof entry.label !== "string" ||
			typeof entry.architecture !== "string" ||
			!isAvailability(entry.availability.adjudication) ||
			!isAvailability(entry.availability.mesh)
		) {
			throw new SimulationApiError("Fixture case catalog was malformed.");
		}
		return {
			caseId: entry.case_id,
			label: entry.label,
			architecture: entry.architecture,
			availability: {
				adjudication: entry.availability.adjudication,
				mesh: entry.availability.mesh,
			},
		};
	});
	return {
		fixture: { corpusId, kind },
		provenance: { claimBoundary, sourceKind },
		cases,
	};
}

function parseFixtureCase(body: unknown): FixtureCaseResponse {
	const envelope = parseEnvelope(body);
	if (!isRecord(body) || !isRecord(body.case)) {
		throw new SimulationApiError("Fixture case detail was malformed.");
	}
	const { architecture, inputs, label } = body.case;
	if (
		!isRecord(inputs) ||
		typeof architecture !== "string" ||
		typeof label !== "string" ||
		!isFiniteNumber(inputs.coating_shear_limit_mpa) ||
		!isFiniteNumber(inputs.mechanical_load_kn) ||
		!isFiniteNumber(inputs.thermal_gradient_c_per_mm)
	) {
		throw new SimulationApiError("Fixture case detail was malformed.");
	}
	return {
		...envelope,
		case: {
			architecture,
			label,
			inputs: {
				coatingShearLimitMpa: inputs.coating_shear_limit_mpa,
				mechanicalLoadKn: inputs.mechanical_load_kn,
				thermalGradientCPerMm: inputs.thermal_gradient_c_per_mm,
			},
		},
	};
}

function parseFixtureAdjudication(body: unknown): FixtureAdjudicationResponse {
	const envelope = parseEnvelope(body);
	if (!isRecord(body) || !isRecord(body.adjudication))
		throw new SimulationApiError("Fixture adjudication was malformed.");
	const {
		quantity,
		surrogate_value: surrogateValue,
		units,
	} = body.adjudication;
	if (
		typeof quantity !== "string" ||
		!isFiniteNumber(surrogateValue) ||
		typeof units !== "string"
	)
		throw new SimulationApiError("Fixture adjudication was malformed.");
	return { ...envelope, adjudication: { quantity, surrogateValue, units } };
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
	const envelope = parseEnvelope(body);
	if (!isRecord(body) || !isRecord(body.run)) {
		throw new SimulationApiError(
			"Fixture reference-run response was malformed.",
		);
	}
	const { case_id: caseId, run_id: runId, status } = body.run;
	if (
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
		...envelope,
		run: { caseId, runId, status },
	};
}

function parseReferenceRunResult(body: unknown): ReferenceRunResultResponse {
	const envelope = parseEnvelope(body);
	if (!isRecord(body) || !isRecord(body.result)) {
		throw new SimulationApiError(
			"Fixture reference-run result response was malformed.",
		);
	}
	const { quantity, units, value } = body.result;
	if (
		typeof quantity !== "string" ||
		typeof units !== "string" ||
		typeof value !== "number"
	) {
		throw new SimulationApiError(
			"Fixture reference-run result response was malformed.",
		);
	}
	return {
		...envelope,
		result: { quantity, units, value },
	};
}

function parseFixtureVerification(body: unknown): FixtureVerificationResponse {
	const envelope = parseEnvelope(body);
	if (!isRecord(body) || !isRecord(body.verification)) {
		throw new SimulationApiError(
			"Fixture verification response was malformed.",
		);
	}
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
		...envelope,
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

function parseEnvelope(body: unknown): {
	fixture: FixtureDescriptor;
	provenance: FixtureProvenance;
} {
	if (
		!isRecord(body) ||
		body.api_version !== "v1" ||
		!isRecord(body.fixture) ||
		!isRecord(body.provenance)
	) {
		throw new SimulationApiError("Fixture response was malformed.");
	}
	const { case_id: caseId, corpus_id: corpusId, kind, revision } = body.fixture;
	const {
		claim_boundary: claimBoundary,
		reference_solution: referenceSolution,
		source_kind: sourceKind,
		surrogate,
	} = body.provenance;
	if (
		typeof corpusId !== "string" ||
		typeof caseId !== "string" ||
		typeof revision !== "string" ||
		kind !== "representative" ||
		sourceKind !== "fixture" ||
		typeof claimBoundary !== "string" ||
		!isRecord(referenceSolution) ||
		typeof referenceSolution.model_id !== "string" ||
		typeof referenceSolution.solver_configuration_id !== "string" ||
		typeof referenceSolution.discretization_id !== "string"
	) {
		throw new SimulationApiError("Fixture response was malformed.");
	}
	const decodedSurrogate = decodeSurrogate(surrogate);
	return {
		fixture: { caseId, corpusId, kind, revision },
		provenance: {
			claimBoundary,
			referenceSolution: {
				discretizationId: referenceSolution.discretization_id,
				modelId: referenceSolution.model_id,
				solverConfigurationId: referenceSolution.solver_configuration_id,
			},
			sourceKind,
			...(decodedSurrogate ? { surrogate: decodedSurrogate } : {}),
		},
	};
}

function decodeSurrogate(value: unknown): SurrogateProvenance | undefined {
	if (value === undefined) return undefined;
	if (
		!isRecord(value) ||
		typeof value.domain_id !== "string" ||
		typeof value.model_id !== "string"
	) {
		throw new SimulationApiError("Fixture response was malformed.");
	}
	return { domainId: value.domain_id, modelId: value.model_id };
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

function isAvailability(value: unknown): value is "available" | "unavailable" {
	return value === "available" || value === "unavailable";
}

function isFiniteNumber(value: unknown): value is number {
	return typeof value === "number" && Number.isFinite(value);
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null;
}

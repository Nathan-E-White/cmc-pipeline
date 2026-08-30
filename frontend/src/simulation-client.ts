export type FixtureInputs = {
	coatingShearLimitMpa: number
	mechanicalLoadKn: number
	thermalGradientCPerMm: number
}

export type ReferenceRunSubmission = {
	caseId: string
	inputs: FixtureInputs
}

export type ReferenceRun = {
	runId: string
	caseId: string
	status: "queued" | "running" | "complete" | "failed"
}

export type HttpRequest = {
	method: "POST"
	path: string
	body: unknown
}

export type HttpResponse = {
	status: number
	body: unknown
}

export type HttpTransport = {
	request: (request: HttpRequest) => Promise<HttpResponse>
}

export class SimulationApiError extends Error {
	constructor(message: string) {
		super(message)
		this.name = "SimulationApiError"
	}
}

export function createSimulationClient(transport: HttpTransport) {
	return {
		submitReferenceRun: async (submission: ReferenceRunSubmission): Promise<ReferenceRun> => {
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
			})
			if (response.status !== 202) {
				throw new SimulationApiError("Fixture reference-run submission was not accepted.")
			}
			return parseReferenceRun(response.body)
		},
	}
}

export function createFetchTransport(fetchImplementation: typeof fetch = fetch): HttpTransport {
	return {
		request: async ({ body, method, path }) => {
			const response = await fetchImplementation(path, {
				method,
				headers: { Accept: "application/json", "Content-Type": "application/json" },
				body: JSON.stringify(body),
			})
			return { status: response.status, body: await response.json() }
		},
	}
}

function parseReferenceRun(body: unknown): ReferenceRun {
	if (!isRecord(body) || !isRecord(body.run)) {
		throw new SimulationApiError("Fixture reference-run response was malformed.")
	}
	const { case_id: caseId, run_id: runId, status } = body.run
	if (
		typeof caseId !== "string" ||
		typeof runId !== "string" ||
		(status !== "queued" && status !== "running" && status !== "complete" && status !== "failed")
	) {
		throw new SimulationApiError("Fixture reference-run response was malformed.")
	}
	return { caseId, runId, status }
}

function isRecord(value: unknown): value is Record<string, unknown> {
	return typeof value === "object" && value !== null
}

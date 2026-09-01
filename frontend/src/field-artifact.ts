export type FieldArtifactResponse =
	| {
			version: "cmc.field-artifact.v1";
			state: "available";
			payload: {
				geometry: { positions: number[][]; triangles: number[][] };
				field: {
					id: string;
					name: string;
					units: string;
					association: "node";
					components: number;
					values: number[][];
				};
				provenance: {
					run_id: string;
					case_digest: string;
					outcome: string | null;
					evidence_disposition: string | null;
					claim_boundary: string;
					artifact_digests: Record<string, string>;
				};
			};
	  }
	| {
			version: "cmc.field-artifact.v1";
			state: "unavailable" | "indeterminate";
			reason: string;
			provenance: {
				run_id: string;
				case_digest: string;
				outcome: string | null;
				evidence_disposition: string | null;
			};
	  };

export function parseFieldArtifact(value: unknown): FieldArtifactResponse {
	if (!value || typeof value !== "object")
		throw new Error("Field artifact response was malformed.");
	const response = value as Record<string, unknown>;
	if (response.version !== "cmc.field-artifact.v1")
		throw new Error("Unsupported field artifact version.");
	if (
		response.state === "available" &&
		response.payload &&
		typeof response.payload === "object"
	)
		return response as FieldArtifactResponse;
	if (
		(response.state === "unavailable" || response.state === "indeterminate") &&
		typeof response.reason === "string"
	)
		return response as FieldArtifactResponse;
	throw new Error("Field artifact response was malformed.");
}

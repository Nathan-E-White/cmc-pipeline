import { createEffect, createSignal, Show } from "solid-js";

import {
	parseFieldArtifact,
	type FieldArtifactResponse,
} from "../field-artifact";

export function RunFieldViewer(props: { runId: string }) {
	const [response, setResponse] = createSignal<FieldArtifactResponse>();
	const [error, setError] = createSignal<string>();
	createEffect(() => {
		void fetch(`/api/v3/runs/${props.runId}/field-artifact`)
			.then(async (result) => {
				if (!result.ok) throw new Error("Field artifact unavailable.");
				return parseFieldArtifact(await result.json());
			})
			.then(setResponse)
			.catch((cause: unknown) =>
				setError(
					cause instanceof Error
						? cause.message
						: "Field artifact unavailable.",
				),
			);
	});
	return <FieldViewer response={response()} error={error()} />;
}

export function FieldViewer(props: {
	response: FieldArtifactResponse | undefined;
	error?: string;
}) {
	const response = () => props.response;
	const available = () => response()?.state === "available";
	return (
		<section
			class="field-artifact-viewer"
			aria-label="Accepted reference field viewer"
		>
			<Show when={props.error}>
				<output>{props.error}</output>
			</Show>
			{available() ? (
				<AvailableField
					response={
						response() as Extract<FieldArtifactResponse, { state: "available" }>
					}
				/>
			) : (
				<FieldState response={response()} />
			)}
		</section>
	);
}

function FieldState(props: { response: FieldArtifactResponse | undefined }) {
	if (!props.response) return <output>Field artifact unavailable.</output>;
	return (
		<output>{`${props.response.state}: ${(props.response as Exclude<FieldArtifactResponse, { state: "available" }>).reason}`}</output>
	);
}

function AvailableField(props: {
	response: Extract<FieldArtifactResponse, { state: "available" }>;
}) {
	const { field, geometry, provenance } = props.response.payload;
	const magnitudes = field.values.map((value) => Math.hypot(...value));
	const min = Math.min(...magnitudes);
	const max = Math.max(...magnitudes);
	const xs = geometry.positions.map((position) => position[0]);
	const ys = geometry.positions.map((position) => position[1]);
	const minX = Math.min(...xs);
	const minY = Math.min(...ys);
	const spanX = Math.max(Math.max(...xs) - minX, Number.EPSILON);
	const spanY = Math.max(Math.max(...ys) - minY, Number.EPSILON);
	const point = (index: number) => {
		const [x, y] = geometry.positions[index];
		return `${((x - minX) / spanX) * 100},${100 - ((y - minY) / spanY) * 100}`;
	};
	const colour = (triangle: number[]) => {
		const value = triangle.reduce((sum, index) => sum + magnitudes[index], 0) / triangle.length;
		const ratio = max === min ? 0.5 : (value - min) / (max - min);
		return `hsl(${220 - ratio * 220} 70% 48%)`;
	};
	return (
		<>
			<header>
				<small>Accepted reference artifact</small>
				<h3>{field.name}</h3>
				<p>
					{field.units} · {field.association} values · {field.components}{" "}
					components
				</p>
			</header>
			<svg
				viewBox="0 0 100 100"
				role="img"
				aria-label={`${field.name} field in ${field.units}`}
			>
				{geometry.triangles.map((triangle) => (
					<polygon
						points={triangle.map(point).join(" ")}
						fill={colour(triangle)}
					/>
				))}
			</svg>
			<p>{`Magnitude legend: ${min.toPrecision(4)}–${max.toPrecision(4)} ${field.units}`}</p>
			<p>
				run: {provenance.run_id} · case: {provenance.case_digest}
			</p>
			<p>
				outcome: {provenance.outcome ?? "unavailable"} · disposition:{" "}
				{provenance.evidence_disposition ?? "unavailable"}
			</p>
			<p>boundary: {provenance.claim_boundary}</p>
			<p>{`artifact identities: ${Object.entries(provenance.artifact_digests).map(([role, digest]) => `${role}:${digest}`).join(" · ")}`}</p>
		</>
	);
}

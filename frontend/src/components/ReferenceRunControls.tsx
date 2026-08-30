import { createSignal, Show } from "solid-js";

import type {
	ReferenceRun,
	ReferenceRunResult,
	ReferenceRunSubmission,
	SimulationClient,
} from "../simulation-client";

type Props = {
	client: SimulationClient;
	submission: ReferenceRunSubmission;
};

export function ReferenceRunControls(props: Props) {
	const [run, setRun] = createSignal<ReferenceRun>();
	const [result, setResult] = createSignal<ReferenceRunResult>();
	const [error, setError] = createSignal<string>();
	const [isSubmitting, setIsSubmitting] = createSignal(false);
	const [isObserving, setIsObserving] = createSignal(false);

	const submit = async () => {
		setError(undefined);
		setResult(undefined);
		setIsSubmitting(true);
		try {
			const response = await props.client.submitReferenceRun(props.submission);
			setRun(response.run);
			const observed = await props.client.getReferenceRun(response.run.runId);
			setRun(observed.run);
			if (observed.run.status === "complete") {
				const resultResponse = await props.client.getReferenceRunResult(
					observed.run.runId,
				);
				setResult(resultResponse.result);
			}
		} catch {
			setRun(undefined);
			setError("The declared fixture reference run could not be submitted.");
		} finally {
			setIsSubmitting(false);
		}
	};

	const observe = async () => {
		const activeRun = run();
		if (!activeRun) return;
		setError(undefined);
		setIsObserving(true);
		try {
			const response = await props.client.getReferenceRun(activeRun.runId);
			setRun(response.run);
			if (response.run.status === "complete") {
				const resultResponse = await props.client.getReferenceRunResult(
					response.run.runId,
				);
				setResult(resultResponse.result);
			}
		} catch {
			setError("The fixture reference-run state could not be observed.");
		} finally {
			setIsObserving(false);
		}
	};

	return (
		<section aria-label="Fixture reference run" class="reference-run-controls">
			<button disabled={isSubmitting()} onClick={submit} type="button">
				Submit fixture reference run
			</button>
			<Show when={run() && run()?.status !== "complete"}>
				<button disabled={isObserving()} onClick={observe} type="button">
					Observe reference run
				</button>
			</Show>
			<Show when={run()}>
				{(activeRun) => <p>{formatRunStatus(activeRun().status)}</p>}
			</Show>
			<Show when={result()}>
				{(referenceResult) => (
					<p>{`${referenceResult().quantity}: ${referenceResult().value} ${referenceResult().units}`}</p>
				)}
			</Show>
			<Show when={error()}>{(message) => <p role="alert">{message()}</p>}</Show>
		</section>
	);
}

function formatRunStatus(status: ReferenceRun["status"]): string {
	return `${status[0].toUpperCase()}${status.slice(1)} fixture reference run`;
}

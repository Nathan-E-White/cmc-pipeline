import { createFileRoute } from "@tanstack/solid-router";
import { RunFieldViewer } from "../components/FieldViewer";
export const Route = createFileRoute("/runs/$runId")({ component: RunResult });
function RunResult() {
	const { runId } = Route.useParams()();
	return (
		<main aria-label="Physics result">
			<p class="eyebrow">CMC Pipeline · physics results</p>
			<h1>Run {runId}</h1>
			<RunFieldViewer runId={runId} />
		</main>
	);
}

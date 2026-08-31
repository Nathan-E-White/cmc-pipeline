import { createSignal, For, Show } from "solid-js";

import { declaredFixtureSurrogateObservation } from "../fixture-surrogate";
import type {
	FixtureDescriptor,
	FixtureProvenance,
	FixtureVerification,
	ReferenceRun,
	ReferenceRunResult,
	ReferenceRunSubmission,
	SimulationClient,
} from "../simulation-client";

type Props = { client: SimulationClient; submission: ReferenceRunSubmission };

type RegisterRecord = {
	adjudicationProvenance?: FixtureProvenance;
	fixture: FixtureDescriptor;
	referenceProvenance: FixtureProvenance;
	resultProvenance?: FixtureProvenance;
	result?: ReferenceRunResult;
	run: ReferenceRun;
	verification?: FixtureVerification;
};

export function ReferenceRunControls(props: Props) {
	const [records, setRecords] = createSignal<RegisterRecord[]>([]);
	const [error, setError] = createSignal<string>();
	const [isSubmitting, setIsSubmitting] = createSignal(false);

	const submit = async () => {
		setError(undefined);
		setIsSubmitting(true);
		try {
			const submitted = await props.client.submitReferenceRun(props.submission);
			const observed = await props.client.getReferenceRun(submitted.run.runId);
			const record: RegisterRecord = {
				fixture: observed.fixture,
				referenceProvenance: observed.provenance,
				run: observed.run,
			};
			if (observed.run.status === "complete") {
				const result = await props.client.getReferenceRunResult(
					observed.run.runId,
				);
				const verification = await props.client.verifySurrogateObservation(
					observed.run.runId,
					props.submission,
					declaredFixtureSurrogateObservation(),
				);
				record.result = result.result;
				record.resultProvenance = result.provenance;
				record.verification = verification.verification;
				record.adjudicationProvenance = verification.provenance;
			}
			setRecords((current) => [record, ...current]);
		} catch {
			setError("The declared fixture reference run could not be recorded.");
		} finally {
			setIsSubmitting(false);
		}
	};

	return (
		<main class="register-prototype" aria-label="Fixture Run Register">
			<header class="register-masthead">
				<div>
					<p class="eyebrow">CMC Pipeline · V1 fixture client</p>
					<h1>RUN REGISTER</h1>
				</div>
				<p class="fixture-stamp">
					REPRESENTATIVE FIXTURE · NOT SOLVER EXECUTION
				</p>
			</header>
			<section class="ledger-layout" aria-label="Fixture reference-run ledger">
				<aside class="ledger-sidebar">
					<p class="section-label">Browser-session register</p>
					<h2>Recorded comparison evidence.</h2>
					<p>
						Each row is an in-memory V1 fixture record. Completion and
						adjudication remain declared fixture outcomes.
					</p>
					<button disabled={isSubmitting()} onClick={submit} type="button">
						{isSubmitting()
							? "Recording fixture run…"
							: "Record fixture reference run"}
					</button>
				</aside>
				<div class="ledger-table-wrap">
					<table class="ledger-table">
						<thead>
							<tr>
								<th>Run</th>
								<th>State</th>
								<th>Reference result</th>
								<th>Adjudication</th>
							</tr>
						</thead>
						<tbody>
							<For
								each={records()}
								fallback={
									<tr>
										<td colSpan={4}>
											No fixture records in this browser session.
										</td>
									</tr>
								}
							>
								{(record) => (
									<tr>
										<td>
											<b>{record.run.runId}</b>
											<small>
												{record.fixture.corpusId} · {record.fixture.caseId} · r
												{record.fixture.revision}
											</small>
										</td>
										<td>{formatRunStatus(record.run.status)}</td>
										<td>
											{record.result
												? `${record.result.quantity}: ${record.result.value} ${record.result.units}`
												: "Unavailable"}
										</td>
										<td>
											{record.verification
												? formatVerificationStatus(record.verification.status)
												: "Unavailable"}
										</td>
									</tr>
								)}
							</For>
						</tbody>
					</table>
					<Show when={records()[0]}>
						{(record) => (
							<aside class="run-detail is-compact">
								<p class="section-label">Latest recorded evidence</p>
								<h2>{record().run.runId}</h2>
								<p class="detail-phase">
									{
										(record().resultProvenance ?? record().referenceProvenance)
											.claimBoundary
									}
								</p>
								<section>
									<h3>Reference solution</h3>
									<p>
										{
											(
												record().resultProvenance ??
												record().referenceProvenance
											).referenceSolution.modelId
										}{" "}
										·{" "}
										{
											(
												record().resultProvenance ??
												record().referenceProvenance
											).referenceSolution.solverConfigurationId
										}{" "}
										·{" "}
										{
											(
												record().resultProvenance ??
												record().referenceProvenance
											).referenceSolution.discretizationId
										}
									</p>
								</section>
								<Show when={record().adjudicationProvenance}>
									{(provenance) => (
										<section>
											<h3>Fixture adjudication scope</h3>
											<p>{provenance().claimBoundary}</p>
										</section>
									)}
								</Show>
								<Show when={record().adjudicationProvenance?.surrogate}>
									{(surrogate) => (
										<section>
											<h3>Surrogate</h3>
											<p>
												{surrogate().modelId} · {surrogate().domainId}
											</p>
										</section>
									)}
								</Show>
								<section>
									<h3>Session</h3>
									<p>
										Browser-session fixture record only; no solver execution,
										persistence, or qualification claim.
									</p>
								</section>
							</aside>
						)}
					</Show>
					<Show when={error()}>
						{(message) => <p role="alert">{message()}</p>}
					</Show>
				</div>
			</section>
		</main>
	);
}

function formatVerificationStatus(
	status: FixtureVerification["status"],
): string {
	return `${status[0].toUpperCase()}${status.slice(1)} fixture adjudication`;
}

function formatRunStatus(status: ReferenceRun["status"]): string {
	return `${status[0].toUpperCase()}${status.slice(1)} fixture reference run`;
}

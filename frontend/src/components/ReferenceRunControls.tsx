import { createSignal, For, onMount, Show } from "solid-js";

import type {
	FixtureCaseResponse,
	FixtureCaseSummary,
	FixtureDescriptor,
	FixtureProvenance,
	FixtureVerification,
	ReferenceRun,
	ReferenceRunResult,
	ReferenceRunSubmission,
	SimulationClient,
	SurrogateObservation,
} from "../simulation-client";

type Props = { client: SimulationClient };

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
	const [cases, setCases] = createSignal<FixtureCaseSummary[]>([]);
	const [selectedCase, setSelectedCase] = createSignal<FixtureCaseResponse>();
	const [selectedCaseId, setSelectedCaseId] = createSignal<string>();
	const [selectedObservation, setSelectedObservation] =
		createSignal<SurrogateObservation>();
	const [isLoadingCase, setIsLoadingCase] = createSignal(true);

	const loadCase = async (caseId: string) => {
		setSelectedCaseId(caseId);
		setSelectedCase(undefined);
		setSelectedObservation(undefined);
		setIsLoadingCase(true);
		try {
			const [detail, adjudication] = await Promise.all([
				props.client.getFixtureCase(caseId),
				props.client.getFixtureAdjudication(caseId),
			]);
			if (selectedCaseId() === caseId) {
				setSelectedCase(detail);
				setSelectedObservation({
					quantity: adjudication.adjudication.quantity,
					value: adjudication.adjudication.surrogateValue,
					units: adjudication.adjudication.units,
				});
			}
		} catch {
			if (selectedCaseId() === caseId)
				setError("The declared fixture case could not be loaded.");
		} finally {
			if (selectedCaseId() === caseId) setIsLoadingCase(false);
		}
	};

	onMount(async () => {
		try {
			const catalog = await props.client.listFixtureCases();
			setCases(catalog.cases);
			const initial = catalog.cases.find(
				(caseSummary) => caseSummary.availability.adjudication === "available",
			);
			if (initial) await loadCase(initial.caseId);
			else setIsLoadingCase(false);
		} catch {
			setError("The fixture case catalog could not be loaded.");
			setIsLoadingCase(false);
		}
	});

	const submit = async () => {
		const detail = selectedCase();
		const observation = selectedObservation();
		if (!detail || !observation) return;
		const submission: ReferenceRunSubmission = {
			caseId: detail.fixture.caseId,
			inputs: detail.case.inputs,
		};
		setError(undefined);
		setIsSubmitting(true);
		try {
			const submitted = await props.client.submitReferenceRun(submission);
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
					submission,
					observation,
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
		<main class="run-register" aria-label="Fixture Run Register">
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
					<label class="fixture-selector">
						Declared fixture
						<select
							disabled={isLoadingCase() || isSubmitting()}
							value={selectedCaseId()}
							onChange={(event) => void loadCase(event.currentTarget.value)}
						>
							<For each={cases()}>
								{(caseSummary) => (
									<option
										disabled={
											caseSummary.availability.adjudication !== "available"
										}
										value={caseSummary.caseId}
									>
										{caseSummary.label} · adjudication{" "}
										{caseSummary.availability.adjudication}
									</option>
								)}
							</For>
						</select>
					</label>
					<button
						disabled={isSubmitting() || isLoadingCase() || !selectedCase()}
						onClick={submit}
						type="button"
					>
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

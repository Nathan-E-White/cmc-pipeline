import { cleanup, render, screen } from "@solidjs/testing-library";
import { createComponent } from "solid-js";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

const transport = vi.hoisted(() => {
	type ShapeStreamOptions = {
		params: { table: string };
	};
	class ShapeStream {
		options: ShapeStreamOptions;
		rows: Array<Record<string, unknown>> = [];

		constructor(options: ShapeStreamOptions) {
			this.options = options;
		}
	}
	class Shape {
		static instances: Shape[] = [];
		stream: ShapeStream;
		listeners = new Set<() => void>();

		constructor(stream: ShapeStream) {
			this.stream = stream;
			Shape.instances.push(this);
		}

		get currentRows() {
			return this.stream.rows;
		}

		get rows() {
			return Promise.resolve(this.currentRows);
		}

		subscribe(listener: () => void) {
			this.listeners.add(listener);
			return () => this.listeners.delete(listener);
		}

		emit(rows: Array<Record<string, unknown>>) {
			this.stream.rows = rows;
			for (const listener of this.listeners) listener();
		}
	}
	return { Shape, ShapeStream };
});

vi.mock("@electric-sql/client", () => transport);

import { V3RunRegister } from "./V3RunRegister";

class EventSourceStub {
	static instances: EventSourceStub[] = [];
	listeners = new Map<string, (event: MessageEvent) => void>();

	constructor(readonly url: string) {
		EventSourceStub.instances.push(this);
	}

	addEventListener(type: string, listener: (event: MessageEvent) => void) {
		this.listeners.set(type, listener);
	}

	close() {}
}

const run = {
	run_id: "monitor-test-run",
	revision: "2",
	lifecycle: "running",
	outcome: null,
	evidence_disposition: null,
	current_phase_key: "mesh",
};
const phase = {
	run_id: "monitor-test-run",
	phase_key: "mesh",
	state: "running",
	headline: { text: "mesh audit observed" },
	trend: {},
	warnings: [],
	last_container_observed_at: "2026-09-03T13:00:00Z",
	last_solver_evidence_at: null,
};

function deferred<T>() {
	let resolve!: (value: T) => void;
	const promise = new Promise<T>((done) => {
		resolve = done;
	});
	return { promise, resolve };
}

function shapeFor(table: string) {
	const shape = transport.Shape.instances.find(
		(candidate) => candidate.stream.options.params.table === table,
	);
	if (!shape) throw new Error(`missing ${table} shape`);
	return shape;
}

beforeEach(() => {
	transport.Shape.instances = [];
	EventSourceStub.instances = [];
	vi.stubGlobal("EventSource", EventSourceStub);
});

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
});

test("updates the visible register from the post-hydration run snapshot", async () => {
	const fetchMock = vi.fn().mockResolvedValue({
		ok: true,
		json: async () => ({
			runs: [{ ...run, state: "running", headline: phase.headline, trend: {} }],
			register_sequence: 7,
		}),
	});
	vi.stubGlobal("fetch", fetchMock);
	render(() => createComponent(V3RunRegister, {}));

	expect(fetchMock).toHaveBeenCalledWith("/api/v3/runs");
	expect(
		await screen.findByRole("article", { name: "Run monitor-test-run" }),
	).toBeTruthy();
	expect(
		screen.getByRole("button", { name: /mesh audit observed/i }),
	).toBeTruthy();
});

test("keeps the SSR register visible when Electric bootstraps empty", async () => {
	const fetchMock = vi.fn();
	vi.stubGlobal("fetch", fetchMock);
	render(() =>
		createComponent(V3RunRegister, {
			initialSnapshot: {
				runs: [
					{
						...run,
						revision: 2,
						state: "running",
						headline: phase.headline,
						trend: {},
					},
				],
				register_sequence: 11,
			},
		}),
	);

	expect(
		await screen.findByRole("article", { name: "Run monitor-test-run" }),
	).toBeTruthy();
	expect(fetchMock).not.toHaveBeenCalled();

	shapeFor("run_phase_summary_projections").emit([]);
	shapeFor("run_summary_projections").emit([]);

	expect(
		await screen.findByRole("article", { name: "Run monitor-test-run" }),
	).toBeTruthy();
	expect(EventSourceStub.instances[0].url).toBe(
		"/api/v3/events?after_sequence=11",
	);
});

test("does not start live transport when the SSR snapshot is unavailable", async () => {
	vi.stubGlobal("fetch", vi.fn());
	render(() =>
		createComponent(V3RunRegister, {
			initialSnapshot: {
				runs: [],
				register_sequence: 0,
				unavailableReason: "Run register snapshot unavailable.",
			},
		}),
	);

	expect(
		await screen.findByText("Run register snapshot unavailable."),
	).toBeTruthy();
	expect(EventSourceStub.instances).toHaveLength(0);
	expect(transport.Shape.instances).toHaveLength(0);
});

test("updates the same visible register when Electric Shapes change", async () => {
	vi.stubGlobal(
		"fetch",
		vi.fn().mockResolvedValue({
			ok: true,
			json: async () => ({ runs: [], register_sequence: 7 }),
		}),
	);
	render(() => createComponent(V3RunRegister, {}));
	await screen.findByText("No V3 run summaries available.");
	await vi.waitFor(() => {
		expect(() => shapeFor("run_phase_summary_projections")).not.toThrow();
	});

	shapeFor("run_phase_summary_projections").emit([phase]);
	shapeFor("run_summary_projections").emit([run]);

	expect(
		await screen.findByRole("article", { name: "Run monitor-test-run" }),
	).toBeTruthy();
});

test("opens SSE only after the snapshot is ready", async () => {
	const snapshot = deferred<{ runs: never[]; register_sequence: number }>();
	vi.stubGlobal(
		"fetch",
		vi.fn().mockResolvedValue({ ok: true, json: async () => snapshot.promise }),
	);
	render(() => createComponent(V3RunRegister, {}));
	await Promise.resolve();
	expect(EventSourceStub.instances).toHaveLength(0);

	snapshot.resolve({ runs: [], register_sequence: 23 });
	await screen.findByText("No V3 run summaries available.");

	await vi.waitFor(() => expect(EventSourceStub.instances).toHaveLength(1));
	expect(EventSourceStub.instances[0].url).toBe(
		"/api/v3/events?after_sequence=23",
	);
});

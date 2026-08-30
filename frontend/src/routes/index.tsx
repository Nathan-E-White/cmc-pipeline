import { createFileRoute } from "@tanstack/solid-router"
import { createSignal, onCleanup } from "solid-js"

import { ControlPanel } from "../components/ControlPanel"
import { ThreeViewport } from "../components/ThreeViewport"
import { defaultInputs, nodeCountFor, type SimulationInput, type SimulationSnapshot, type SolverKind } from "../simulation"

export const Route = createFileRoute("/")({ component: Home })

function Home() {
	const [inputs, setInputs] = createSignal(defaultInputs)
	const [snapshot, setSnapshot] = createSignal<SimulationSnapshot>(idle(inputs()))
	let timer: ReturnType<typeof setInterval> | undefined
	const update = (value: Partial<SimulationInput>) => {
		const next = { ...inputs(), ...value }
		setInputs(next)
		if (snapshot().status !== "running") setSnapshot(idle(next))
	}
	const run = (solver: SolverKind) => {
		if (timer) return
		let progress = 0
		const runInputs = inputs()
		setSnapshot((current) => ({ ...current, mode: solver === "FEA" ? "Reference field processing" : "Surrogate screening", progress, status: "running", title: `Processing ${solver === "FEA" ? "reference solver" : "surrogate"}` }))
		timer = setInterval(() => {
			progress = Math.min(progress + 0.04, 1)
			setSnapshot((current) => ({ ...current, progress, telemetry: telemetry(runInputs, progress) }))
			if (progress !== 1) return
			clearInterval(timer)
			timer = undefined
			setSnapshot((current) => ({ ...current, mode: "Representative post-run field", runs: { ...current.runs, [solver]: solver === "FEA" ? 6.42 : 0.005 }, status: "complete", title: "Illustrative analysis complete" }))
		}, 50)
	}
	onCleanup(() => { if (timer) clearInterval(timer) })
	return <main class="app-shell"><ControlPanel inputs={inputs} onInput={update} onRun={run} snapshot={snapshot} /><ThreeViewport snapshot={snapshot} /></main>
}

function idle(inputs: SimulationInput): SimulationSnapshot {
	return { mode: "Representative material continuum", progress: 0, runs: { FEA: undefined, FNO: undefined }, status: "idle", telemetry: { area: 0, energy: 0, margin: 1.5, nodes: nodeCountFor(inputs.architecture) }, title: "System ready" }
}
function telemetry(inputs: SimulationInput, progress: number) {
	const load = inputs.mechanicalLoad / 45
	const thermal = inputs.thermalGradient / 120
	const resistance = inputs.coatingStrength / 60
	const extent = Math.min((2.8 * load * thermal) / resistance, 2.9) * progress
	return { area: extent * 20, energy: load * thermal * 180 * progress, margin: resistance * 1.5 - load * thermal * progress * 1.4, nodes: nodeCountFor(inputs.architecture) }
}

#!/usr/bin/env node

/**
 * Configuration-only entry point for bounded local resilience experiments.
 * It validates manifests and prints their scope; it deliberately cannot inject
 * a fault until the probe and recovery drivers are implemented in a later slice.
 */
import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = process.cwd();
const suitePath = resolve(root, "resilience/suite.v1.json");
const experimentsPath = resolve(root, "resilience/experiments");
const allowedFaults = new Set(["pause", "stop", "kill", "toxiproxy-reset", "toxiproxy-timeout"]);

function fail(message) {
  throw new Error(message);
}

async function json(path) {
  try {
    return JSON.parse(await readFile(path, "utf8"));
  } catch (error) {
    fail(`Cannot read JSON ${path}: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function validateSuite(suite) {
  if (suite.version !== "cmc.resilience-suite.v1") fail("Unsupported resilience suite version.");
  if (suite.environment !== "local-development") fail("Only local-development is permitted.");
  if (suite.docker_context !== "orbstack") fail("Docker context must be orbstack.");
  if (!suite.compose_project || !suite.evidence_directory) fail("Suite needs compose_project and evidence_directory.");
  for (const [name, seconds] of Object.entries(suite.limits ?? {})) {
    if (!Number.isInteger(seconds) || seconds < 1) fail(`Invalid suite limit ${name}.`);
  }
}

function validateExperiment(experiment, suite) {
  const required = ["id", "title", "state", "hypothesis", "target", "fault", "probes", "assertions"];
  for (const key of required) if (!(key in experiment)) fail(`${experiment.id ?? "unknown"}: missing ${key}.`);
  if (!allowedFaults.has(experiment.fault.kind)) fail(`${experiment.id}: unsupported fault ${experiment.fault.kind}.`);
  if (!Number.isInteger(experiment.fault.duration_seconds) || experiment.fault.duration_seconds < 1) {
    fail(`${experiment.id}: fault duration must be a positive integer.`);
  }
  if (experiment.fault.duration_seconds >= suite.limits.total_seconds) fail(`${experiment.id}: fault exceeds total limit.`);
  for (const phase of ["baseline", "during_fault", "recovery"]) {
    if (!Array.isArray(experiment.probes[phase]) || experiment.probes[phase].length === 0) {
      fail(`${experiment.id}: ${phase} needs at least one public probe.`);
    }
  }
  if (experiment.target.kind === "container") {
    const service = suite.services?.[experiment.target.service];
    if (!service?.fault_opt_in) fail(`${experiment.id}: target service is not opted in.`);
  }
  if (experiment.target.kind === "toxiproxy" && !experiment.target.route) {
    fail(`${experiment.id}: toxiproxy target needs a route.`);
  }
}

async function load() {
  const suite = await json(suitePath);
  validateSuite(suite);
  const filenames = (await readdir(experimentsPath)).filter((name) => name.endsWith(".json")).sort();
  const experiments = await Promise.all(filenames.map(async (name) => json(resolve(experimentsPath, name))));
  for (const experiment of experiments) validateExperiment(experiment, suite);
  return { suite, experiments };
}

function printPlan(suite, experiments) {
  console.log(`Suite ${suite.version} — ${suite.environment}`);
  console.log(`Docker context: ${suite.docker_context}; Compose project: ${suite.compose_project}`);
  for (const experiment of experiments) {
    const target = experiment.target.service ?? experiment.target.route;
    console.log(`${experiment.id} [${experiment.state}] ${experiment.fault.kind} -> ${target}; recovery=${experiment.fault.recovery}`);
  }
}

const [command = "plan", selectedId, executeFlag] = process.argv.slice(2);
const { suite, experiments } = await load();
if (command === "plan" || command === "status") {
  const selected = selectedId ? experiments.filter((item) => item.id === selectedId) : experiments;
  if (selectedId && selected.length === 0) fail(`Unknown experiment: ${selectedId}`);
  printPlan(suite, selected);
} else if (command === "run") {
  if (!selectedId) fail("Usage: resilience-orchestrate.mjs run <experiment-id> --execute");
  if (executeFlag !== "--execute") fail("Execution requires the explicit --execute flag.");
  const experiment = experiments.find((item) => item.id === selectedId);
  if (!experiment) fail(`Unknown experiment: ${selectedId}`);
  fail(`${experiment.id} is configuration-only: probe and recovery drivers have not been implemented, so no fault was injected.`);
} else {
  fail(`Usage: resilience-orchestrate.mjs [plan|status|run <experiment-id> --execute]`);
}

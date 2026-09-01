#!/usr/bin/env sh
set -eu

manifest="resilience/backend-pause.json"
evidence_dir=".local/resilience-evidence"
mkdir -p "${evidence_dir}"
node -e '
const plan = JSON.parse(require("fs").readFileSync(process.argv[1], "utf8"));
if (plan.docker_context !== "orbstack" || plan.service !== "backend" || plan.fault?.kind !== "pause" || plan.fault?.duration_seconds !== 5 || plan.limits?.total_seconds > 45) process.exit(1);
' "${manifest}"
test "${1:-}" = "--execute" || { echo "plan: ${manifest}; pass --execute"; exit 0; }

container=$(docker --context orbstack compose ps -q backend)
test -n "${container}"
label=$(docker --context orbstack inspect -f '{{ index .Config.Labels "com.radiant.chaos-enabled" }}' "${container}")
test "${label}" = "true"
curl -fsS http://127.0.0.1:8000/api/v1/cases >/dev/null
trap 'docker --context orbstack unpause "${container}" >/dev/null 2>&1 || true' EXIT
docker --context orbstack pause "${container}" >/dev/null
sleep 5
if curl --max-time 2 -fsS http://127.0.0.1:8000/api/v1/cases >/dev/null; then
  echo '{"verdict":"failed","reason":"probe remained available during pause"}' > "${evidence_dir}/backend-pause.json"
  exit 1
fi
docker --context orbstack unpause "${container}" >/dev/null
trap - EXIT
curl --max-time 15 --retry 5 --retry-connrefused -fsS http://127.0.0.1:8000/api/v1/cases >/dev/null
printf '%s\n' '{"verdict":"passed","fault":"backend pause","recovery":"unpause and HTTP probe passed"}' > "${evidence_dir}/backend-pause.json"

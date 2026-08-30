#!/usr/bin/env bash
set -euo pipefail

context="${DOCKER_CONTEXT:-orbstack}"
image="${REFERENCE_SOLVER_IMAGE:-cmc-reference-solver:test}"
output_dir="$(mktemp -d)"
trap 'rm -rf "${output_dir}"' EXIT

docker --context "${context}" build --tag "${image}" --file containers/solver.Dockerfile .
docker --context "${context}" run --rm \
  --volume "${output_dir}:/artifacts" \
  "${image}" \
  converge-case --output /artifacts

test -s "${output_dir}/provenance-convergence.json"
test -s "${output_dir}/case-visual.svg"
python3 reference/tests/validate_convergence_artifact.py "${output_dir}/provenance-convergence.json"
jq 'del(.levels[2].contours[1])' "${output_dir}/provenance-convergence.json" > "${output_dir}/invalid-convergence.json"
! python3 reference/tests/validate_convergence_artifact.py "${output_dir}/invalid-convergence.json"

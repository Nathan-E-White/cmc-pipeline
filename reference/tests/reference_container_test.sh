#!/usr/bin/env bash
set -euo pipefail

context="${DOCKER_CONTEXT:-orbstack}"
image="${REFERENCE_SOLVER_IMAGE:-cmc-reference-solver:test}"
output_dir="$(mktemp -d)"
bridged_output_dir="$(mktemp -d)"
trap 'rm -rf "${output_dir}" "${bridged_output_dir}"' EXIT

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

docker --context "${context}" run --rm \
  --volume "${bridged_output_dir}:/artifacts" \
  "${image}" \
  converge-bridged-case --output /artifacts

test -s "${bridged_output_dir}/provenance-convergence.json"
test -s "${bridged_output_dir}/case-visual.svg"
python3 reference/tests/validate_bridged_convergence_artifact.py "${bridged_output_dir}/provenance-convergence.json"
jq 'del(.comparison.fine_medium_change_percent)' "${bridged_output_dir}/provenance-convergence.json" > "${bridged_output_dir}/invalid-bridged-convergence.json"
! python3 reference/tests/validate_bridged_convergence_artifact.py "${bridged_output_dir}/invalid-bridged-convergence.json"

reversible_output_dir="$(mktemp -d)"
trap 'rm -rf "${output_dir}" "${bridged_output_dir}" "${reversible_output_dir}"' EXIT
docker --context "${context}" run --rm \
  --volume "${reversible_output_dir}:/artifacts" \
  "${image}" \
  converge-reversible-cohesive-case --output /artifacts
test -s "${reversible_output_dir}/reversible-cohesive-convergence.json"
python3 reference/tests/validate_reversible_cohesive_convergence_artifact.py "${reversible_output_dir}/reversible-cohesive-convergence.json"

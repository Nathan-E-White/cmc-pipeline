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
  verify-case --output /artifacts

test -s "${output_dir}/mesh-audit.json"
test -s "${output_dir}/environment.json"
test "$(jq -r '.status' "${output_dir}/mesh-audit.json")" = "accepted"
test "$(jq -r '.mesh.minimum_quality >= 0.2' "${output_dir}/mesh-audit.json")" = "true"
test "$(jq -r '.dolfinx_version' "${output_dir}/environment.json")" != "unavailable"

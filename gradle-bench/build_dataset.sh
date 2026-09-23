#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATASET="$SCRIPT_DIR/data/gradle_benchmark_dataset_representative_100.json"
IMAGE_NAMESPACE="gradlebench"
GATEWAY_DIR="$SCRIPT_DIR/registry_proxy"
PYTHON_BIN="${PYTHON_BIN:-python}"

# Drop the dataset arg if present, leaving any remaining args to forward to
# prepare_images (e.g. --rebuild_failures, --force_rebuild true,
# --instance_ids id1 id2, --push).
if (($#)) && [[ $1 != -* ]]; then
  DATASET="$1"
  shift
fi

start_dependency_gateway() {
  local compose_args=()
  local state_dir="${DEPENDENCY_GATEWAY_STATE_DIR:-$GATEWAY_DIR/.state}"

  if [[ -n ${DEPENDENCY_GATEWAY_ENV_FILE:-} ]]; then
    [[ -f $DEPENDENCY_GATEWAY_ENV_FILE ]] || {
      echo "ERROR: dependency gateway configuration not found: $DEPENDENCY_GATEWAY_ENV_FILE" >&2
      exit 1
    }
    compose_args+=(--env-file "$DEPENDENCY_GATEWAY_ENV_FILE")
    [[ -n ${DEPENDENCY_GATEWAY_CA_CERT:-} ]] || {
      echo "ERROR: DEPENDENCY_GATEWAY_CA_CERT is required with DEPENDENCY_GATEWAY_ENV_FILE" >&2
      exit 1
    }
  else
    compose_args+=(--env-file /dev/null)
    DEPENDENCY_GATEWAY_STATE_DIR="$state_dir" "$GATEWAY_DIR/generate_certificates.sh"
    export TLS_CERT_FILE="$state_dir/tls.crt"
    export TLS_KEY_FILE="$state_dir/tls.key"
    export DEPENDENCY_GATEWAY_CA_CERT="$state_dir/ca.crt"
  fi

  docker compose version >/dev/null 2>&1 || {
    echo "ERROR: docker compose is required to start the dependency gateway" >&2
    exit 1
  }
  echo "=== dependency registry gateway"
  docker compose \
    "${compose_args[@]}" \
    --project-directory "$GATEWAY_DIR" \
    -f "$GATEWAY_DIR/compose.yaml" \
    up -d --force-recreate --wait --wait-timeout 60
  export DEPENDENCY_GATEWAY=host-gateway
}

if [[ ! -v DEPENDENCY_GATEWAY ]]; then
  start_dependency_gateway
fi

# 1. Extend the dataset in place with per-task "test_cmd" and "image_name"
#    fields resolved from MAP_REPO_VERSION_TO_SPECS (includes repo_customization
#    overrides).
"$PYTHON_BIN" "$SCRIPT_DIR/augment_dataset.py" "$DATASET" \
  --namespace "$IMAGE_NAMESPACE" \
  --instance_image_tag latest

# 2. Build a Docker image per task.
"$PYTHON_BIN" -m swebench.harness.prepare_images \
  "$@" \
  --dataset_name "$DATASET" \
  --max_workers 8 \
  --namespace "$IMAGE_NAMESPACE" \
  --tag latest \
  --env_image_tag latest \
  --cache_path "$SCRIPT_DIR/data/build_cache.json"

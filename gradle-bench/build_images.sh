#!/usr/bin/env bash
SCRIPT_DIR="$(dirname "$0")"
DATASET=${1:-$SCRIPT_DIR/data/gradle_benchmark_dataset.json}
# Drop the dataset arg if present, leaving any remaining args to forward to
# prepare_images (e.g. --rebuild_failures, --force_rebuild true,
# --instance_ids id1 id2).
if [ $# -gt 0 ]; then shift; fi

python -m swebench.harness.prepare_images \
  --dataset_name "$DATASET" \
  --max_workers 8 \
  --namespace "" \
  --tag latest \
  --env_image_tag latest \
  --cache_path "$SCRIPT_DIR/data/build_cache.json" \
  "$@"
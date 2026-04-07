#!/usr/bin/env bash
# Usage:
#   ./run_evaluation.sh build    — build images using gradle_benchmark_dataset_reviewed.json
#   ./run_evaluation.sh test     — run tests using gradle_benchmark_dataset_correct_high_with_test_patch.json
#   ./run_evaluation.sh <path/to/dataset.json> <run_id>  — custom dataset and run_id

SCRIPT_DIR="$(dirname "$0")"

case "${1:-}" in
  build)
    DATASET="$SCRIPT_DIR/data/gradle_benchmark_dataset_reviewed.json"
    RUN_ID="gradle_benchmark_v0_build"
    ;;
  test)
    DATASET="$SCRIPT_DIR/data/gradle_benchmark_dataset_correct_high_with_test_patch.json"
    RUN_ID="gradle_benchmark_v0_with_tests"
    ;;
  *)
    if [[ -n "${1:-}" && -n "${2:-}" ]]; then
      DATASET="$1"
      RUN_ID="$2"
    else
      echo "Usage: $0 {build|test|<dataset_path> <run_id>}"
      exit 1
    fi
    ;;
esac

python -m swebench.harness.run_evaluation \
  --dataset_name "$DATASET" \
  --predictions_path gold \
  --max_workers 8 \
  --run_id "$RUN_ID" \
  --namespace "" \
  --cache_level "instance"

python -m swebench.harness.run_evaluation \
  --dataset_name gradle_prs_swe_bench_trimmed.json \
  --predictions_path gold \
  --max_workers 8 \
  --run_id "evaluation-run-1" \
  --namespace "" \
  --cache_level "instance"
#  --force_rebuild True
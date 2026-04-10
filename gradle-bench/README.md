# Gradle SWE-bench Pipeline

This directory contains the benchmark dataset, evaluation configuration, and pipeline tooling for the Gradle SWE-bench benchmark — a curated set of real-world Gradle issues used to evaluate AI agents on software engineering tasks.

---

## Pipeline Overview

```
Raw Dataset  (data/gradle_benchmark_dataset.json)
    │
    ▼
[1] Build Docker Images     — one isolated environment per instance
    │
    ▼
[2] Analyze Build Logs      — determine which instances built successfully
    │
    ▼
[3] Filter to Buildable     — drop failed instances
    │
    ▼
    data/gradle_benchmark_dataset_buildable.json
```

Steps 1–3 are fully automated via `pipeline.py`.

---

## Running the Pipeline

```bash
cd gradle-bench
python pipeline.py
```

Output: `data/gradle_benchmark_dataset_buildable.json`

---

## Files

| File | Purpose |
|---|---|
| `pipeline.py` | Runs the full automated pipeline (steps 1–3) |
| `build_failures.py` | Analyzes build logs; filters dataset to buildable instances |
| `build_images.sh` | Invokes `swebench.harness.prepare_images` with project-specific flags |
| `run_evaluation.sh` | Manual helper: runs `swebench.harness.run_evaluation` against a dataset |
| `data/gradle_benchmark_dataset.json` | Raw input dataset |
| `data/gradle_benchmark_dataset_buildable.json` | Output: instances with successful Docker builds |
| `data/build_analysis.json` | Per-instance build log analysis (success/failure) |
| `data/build_cache.json` | Docker build cache used by `prepare_images` |

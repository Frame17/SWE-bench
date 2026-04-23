# Gradle SWE-bench Pipeline

This directory contains the benchmark dataset, evaluation configuration, and pipeline tooling for the Gradle SWE-bench benchmark — a curated set of real-world Gradle issues used to evaluate AI agents on software engineering tasks.

---

## Pipeline Overview

```
Raw Dataset  (data/gradle_benchmark_dataset.json)
    │
    ▼
[1] Build Docker Images     — one isolated environment per instance
    │                         results recorded in data/build_cache.json
    ▼
[2] Filter to Buildable     — drop instances not marked "success" in build_cache.json
    │
    ▼
    data/gradle_benchmark_dataset_buildable.json
```

Steps 1–2 are fully automated via `pipeline.py`.

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
| `pipeline.py` | Runs the full automated pipeline (steps 1–2) |
| `build_images.sh` | Invokes `swebench.harness.prepare_images` with project-specific flags |
| `run_evaluation.sh` | Manual helper: runs `swebench.harness.run_evaluation` against a dataset |
| `data/gradle_benchmark_dataset.json` | Raw input dataset |
| `data/gradle_benchmark_dataset_buildable.json` | Output: instances with successful Docker builds |
| `data/build_cache.json` | Per-instance build status (`"success"` / `"fail"`); used by `pipeline.py` to filter the dataset |

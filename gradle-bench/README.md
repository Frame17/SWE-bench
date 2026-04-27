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

## Building images directly

Use `build_images.sh` when you want to invoke `swebench.harness.prepare_images` against a specific dataset without running the full pipeline:

```bash
./build_images.sh [DATASET_PATH] [extra prepare_images flags]
```

Anything after the dataset path is forwarded to `prepare_images` verbatim. Useful flags:

| Flag | When to use |
|---|---|
| `--instance_ids ID1 ID2 …` | Build only the listed instances (rest of the dataset is ignored). |
| `--force_rebuild true` | Rebuild every instance regardless of cache state — slow; mainly for full refreshes. |
| `--rebuild_failures` | **Retry only the instances whose cache entry is a previous failure.** Skips cached successes and instances not in the cache. Useful when a transient build issue (network, registry hiccup, runner pressure) caused some images to fail and you want to retry just those without re-running the whole pipeline. |

Example — retry every failed build in the dataset:

```bash
./build_images.sh data/gradle_benchmark_dataset.json --rebuild_failures
```

Example — retry one specific failed build:

```bash
./build_images.sh data/gradle_benchmark_dataset.json \
  --rebuild_failures \
  --instance_ids Kotlin__kotlinx.serialization-2946
```

The build cache (`data/build_cache.json`) records `"success"` or `"fail"` per instance. The script also surfaces:

- Each existing image it found and is reusing (`Found existing image: …`).
- Cached failures it's skipping (with a hint to use `--rebuild_failures`).
- Stale cache entries (`"success"` but image missing from the daemon) it will rebuild automatically.

---

## Files

| File | Purpose |
|---|---|
| `pipeline.py` | Runs the full automated pipeline (steps 1–2) |
| `build_images.sh` | Invokes `swebench.harness.prepare_images` with project-specific flags; forwards extra args |
| `run_evaluation.sh` | Manual helper: runs `swebench.harness.run_evaluation` against a dataset |
| `data/gradle_benchmark_dataset.json` | Raw input dataset |
| `data/gradle_benchmark_dataset_buildable.json` | Output: instances with successful Docker builds |
| `data/build_cache.json` | Per-instance build status (`"success"` / `"fail"`); used by `pipeline.py` to filter the dataset |

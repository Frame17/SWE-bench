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

## Building the dataset directly

Use `build_dataset.sh` when you want to (1) extend a dataset with per-task `test_cmd` and `image_name` fields and (2) build its Docker images, without running the full pipeline:

```bash
./build_dataset.sh [DATASET_PATH] [extra prepare_images flags]
```

The default dataset is `data/gradle_benchmark_dataset_representative_100.json`.
Final images are tagged under `gradlebench/`; shared base and environment images
remain local.

The script first runs `augment_dataset.py` to write `test_cmd` and `image_name` fields into each task **in place** (resolved from `MAP_REPO_VERSION_TO_SPECS`, including `repo_customization` overrides), then invokes `swebench.harness.prepare_images`.

The script also starts the transparent dependency gateway in `registry_proxy/`
unless `DEPENDENCY_GATEWAY` is already set. Set it to an existing gateway
address to use that service, or to an empty value to disable routing. The local
gateway remains running after the build.

Anything after the dataset path is forwarded to `prepare_images` verbatim. Useful flags:

| Flag | When to use |
|---|---|
| `--instance_ids ID1 ID2 …` | Build only the listed instances (rest of the dataset is ignored). |
| `--force_rebuild true` | Rebuild every instance regardless of cache state — slow; mainly for full refreshes. |
| `--rebuild_failures` | **Build every instance that doesn't have a confirmed-good image** in the local Docker daemon. Covers cached failures, stale successes (cache says success but image is gone — e.g. after `docker image prune`), and instances not in the cache at all. Cached successes whose image is present are still skipped. Less broad than `--force_rebuild` (which rebuilds everything regardless of cache). |
| `--push` | Push selected successful final images after building. |

Example — retry every failed build in the dataset:

```bash
./build_dataset.sh data/gradle_benchmark_dataset.json --rebuild_failures
```

Example — retry one specific failed build:

```bash
./build_dataset.sh data/gradle_benchmark_dataset.json \
  --rebuild_failures \
  --instance_ids Kotlin__kotlinx.serialization-2946
```

Example — build and publish one image:

```bash
./build_dataset.sh --rebuild_failures --push \
  --instance_ids Kotlin__kotlinx.serialization-2946
```

Without `--push`, no image is uploaded.

The build cache (`data/build_cache.json`) records `"success"` or `"fail"` per instance. The script also surfaces:

- Each existing image it found and is reusing (`Found existing image: …`).
- Cached failures it's skipping (with a hint to use `--rebuild_failures`).
- Stale cache entries (`"success"` but image missing from the daemon) it will rebuild automatically.

---

## Files

| File | Purpose |
|---|---|
| `pipeline.py` | Runs the full automated pipeline (steps 1–2) |
| `build_dataset.sh` | Starts the dependency gateway, extends the dataset with `test_cmd` and remote `image_name` fields, then builds and optionally publishes images |
| `registry_proxy/` | TLS dependency gateway for Maven Central, the Gradle Plugin Portal, and Reposilite |
| `augment_dataset.py` | Adds `test_cmd` and `image_name` fields to each task, resolved from `MAP_REPO_VERSION_TO_SPECS` |
| `run_evaluation.sh` | Manual helper: runs `swebench.harness.run_evaluation` against a dataset |
| `data/gradle_benchmark_dataset.json` | Raw input dataset |
| `data/gradle_benchmark_dataset_buildable.json` | Output: instances with successful Docker builds |
| `data/build_cache.json` | Per-instance build status (`"success"` / `"fail"`); used by `pipeline.py` to filter the dataset |

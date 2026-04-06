# Gradle SWE-bench Pipeline

This directory contains the benchmark dataset, evaluation configuration, and pipeline tooling for the Gradle SWE-bench benchmark — a curated set of real-world Gradle issues used to evaluate AI agents on software engineering tasks.

---

## Pipeline Overview

The pipeline transforms a raw collection of Gradle issues into a validated, evaluation-ready benchmark. It proceeds through five conceptual stages:

```
Raw Dataset
    │
    ▼
[1] Quality Filtering        — keep only human-approved, high-confidence instances
    │
    ▼
[2] Environment Preparation  — build reproducible Docker environments per instance
    │
    ▼
[3] Environment Validation   — verify builds succeed; drop broken instances
    │
    ▼
[4] Test Patch Generation    — an agent writes test patches that expose each bug
    │
    ▼
[5] Evaluation               — score gold patches against generated test patches
```

Stages 1, 2, and 3 are fully automated. Stage 4 currently requires a manually-run agent. Stage 5 is automated once stage 4 is complete.

---

## Stage Descriptions

### Stage 1 — Quality Filtering

The raw dataset is filtered down to instances that passed human review with a verdict of *correct* and a confidence of *high*. This ensures the benchmark contains only well-formed, unambiguous issues with verifiable solutions.

### Stage 2 — Environment Preparation

Each surviving instance gets its own isolated, reproducible Docker environment. This guarantees that evaluation results are consistent across runs and machines, and that each instance is tested in the exact environment it was originally reported against.

### Stage 3 — Environment Validation

After building, the pipeline checks which instances built successfully. Any instance whose environment could not be reproduced is dropped. This keeps the benchmark honest — only instances that can actually be run are evaluated.

### Stage 4 — Test Patch Generation *(pending)*

An AI agent generates a test patch for each instance. The test patch consists of one or more tests that reproduce the reported bug and fail against the original code. This stage is currently run manually.

### Stage 5 — Evaluation

Gold patches (known correct fixes) are applied to each instance and run against the generated test patches. An instance is considered *resolved* if the gold patch makes all generated tests pass. This measures how well the test patches capture the intended behavior.

---

## Running the Pipeline

All automatable stages (1, 2, 3) can be run together:

```bash
cd gradle-bench
python pipeline.py
```

After completing stage 4 manually, run stage 5 to produce the final evaluation results.

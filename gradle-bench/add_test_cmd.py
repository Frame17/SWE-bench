"""Extend a gradle-bench dataset with a per-task ``test_cmd`` field.

The test command for each task lives only in the Python specs
(``swebench/harness/constants/kotlin_base.py``, overridden per-repo in
``swebench/harness/repo_customization/*.py``) and is resolved as
``MAP_REPO_VERSION_TO_SPECS[repo][version]["test_cmd"]`` (a list of shell
commands). This script bakes that list into the dataset so downstream consumers
read it from the data instead of re-mirroring the constants.

Usage:
  python add_test_cmd.py DATASET.json [--output OUT.json] [--instance_ids ID ...]

The dataset is rewritten in place unless ``--output`` is given. Re-running is
idempotent.
"""
import argparse
import json

from swebench.harness.constants import MAP_REPO_VERSION_TO_SPECS


def add_test_cmd(dataset: list, instance_ids: list | None = None) -> int:
    """Add a ``test_cmd`` field to each task, resolved from the specs.

    Returns the number of tasks augmented. Raises ValueError listing any
    (repo, version) pairs missing from MAP_REPO_VERSION_TO_SPECS.
    """
    missing = set()
    augmented = 0
    for instance in dataset:
        if instance_ids is not None and instance["instance_id"] not in instance_ids:
            continue
        repo = instance["repo"]
        version = instance.get("version")
        specs = MAP_REPO_VERSION_TO_SPECS.get(repo, {}).get(version)
        if specs is None or "test_cmd" not in specs:
            missing.add((repo, version))
            continue
        instance["test_cmd"] = specs["test_cmd"]
        augmented += 1

    if missing:
        pairs = ", ".join(f"{repo}@{version}" for repo, version in sorted(missing))
        raise ValueError(
            f"No test_cmd found in MAP_REPO_VERSION_TO_SPECS for: {pairs}"
        )
    return augmented


def main(dataset_path: str, output: str | None, instance_ids: list | None) -> None:
    with open(dataset_path) as f:
        dataset = json.load(f)

    augmented = add_test_cmd(dataset, instance_ids)

    out_path = output or dataset_path
    with open(out_path, "w") as f:
        json.dump(dataset, f, indent=2)

    print(f"Added test_cmd to {augmented}/{len(dataset)} tasks → {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", help="Path to the dataset JSON file")
    parser.add_argument(
        "--output",
        default=None,
        help="Where to write the augmented dataset (default: in place)",
    )
    parser.add_argument(
        "--instance_ids",
        nargs="+",
        default=None,
        help="Only augment these instance IDs (default: all)",
    )
    args = parser.parse_args()
    main(args.dataset, args.output, args.instance_ids)

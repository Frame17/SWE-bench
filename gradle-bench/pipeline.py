"""
Gradle SWE-bench build pipeline.

Takes the raw dataset, builds Docker images for each instance, and outputs a
dataset containing only the instances whose images built successfully.

Input:  data/gradle_benchmark_dataset.json
Output: data/gradle_benchmark_dataset_buildable.json

Steps:
  build_images    — Build Docker images for all raw instances   (build_images.sh)
  analyze_builds  — Scan build logs, write data/build_analysis.json
  filter_build    — Keep only successfully-built instances       (data/gradle_benchmark_dataset_buildable.json)

Usage:
  python pipeline.py
"""
import subprocess
import sys
import os
import build_failures

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET = os.path.join(BENCH_DIR, 'data', 'gradle_benchmark_dataset.json')


def build_images():
    print("\n--- build_images: Build Docker images ---")
    script = os.path.join(BENCH_DIR, 'build_images.sh')
    result = subprocess.run(['/bin/bash', script, DATASET], stderr=subprocess.PIPE)
    if result.returncode != 0:
        stderr = result.stderr.decode(errors='replace')
        # The Docker SDK has a known race condition: containers cleaned up between
        # containers.list() and containers.get() raise NotFound.  This only happens
        # after all instances have already been evaluated, so the build output is
        # intact.  Treat it as a soft warning rather than a hard failure.
        if 'docker.errors.NotFound' in stderr or 'No such container' in stderr:
            print("WARNING: Docker container race condition in reporting (benign). "
                  "Build stage completed.", file=sys.stderr)
        else:
            print("ERROR: build_images.sh failed.", file=sys.stderr)
            print(stderr, file=sys.stderr)
            sys.exit(result.returncode)


def analyze_builds():
    print("\n--- analyze_builds: Analyze build logs ---")
    build_failures.analyze()


def filter_build():
    print("\n--- filter_build: Keep successfully-built instances ---")
    build_failures.filter_failures()


def main():
    build_images()
    analyze_builds()
    filter_build()
    print("\n--- Done ---")
    print("Buildable dataset written to: data/gradle_benchmark_dataset_buildable.json")


if __name__ == '__main__':
    main()

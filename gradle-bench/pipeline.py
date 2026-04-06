"""
Gradle SWE-bench unified pipeline.

Steps:
  filter_reviews      Filter dataset by human reviews          (filter.py → filter_by_review)
  build_images        Build Docker images                      (run_evaluation.sh build)
  filter_failures     Analyze build logs & filter out failures (build_failures.py)
  generate_patches    Generate test patches                    (pending — run agent manually)
  run_evaluation      Run final evaluation with test patches   (run_evaluation.sh test)

Usage:
  python pipeline.py                              # run all automatable steps (correct + high)
  python pipeline.py --verdict correct            # any confidence
  python pipeline.py --confidence medium          # any verdict
  python pipeline.py --verdict correct --confidence medium
"""
import argparse
import functools
import subprocess
import sys
import os
import filter
import build_failures

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))


def filter_reviews(predicate=None):
    print("\n--- filter_reviews: Filter dataset by human reviews ---")
    filter.filter_by_review(predicate=predicate)


def build_images():
    print("\n--- build_images: Build Docker images ---")
    script = os.path.join(BENCH_DIR, 'run_evaluation.sh')
    result = subprocess.run(['/bin/bash', script, 'build'], stderr=subprocess.PIPE)
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
            print("ERROR: run_evaluation.sh build failed.", file=sys.stderr)
            print(stderr, file=sys.stderr)
            sys.exit(result.returncode)


def filter_failures():
    print("\n--- filter_failures: Analyze build logs & remove failed instances ---")
    build_failures.analyze()
    build_failures.filter_failures()


def generate_patches():
    print("\n--- generate_patches: Generate test patches (pending) ---")
    print("This step is not yet automated.")
    print("Run the agent manually, then place the output at:")
    print("  data/gradle_benchmark_dataset_correct_high_with_test_patch.json")


def run_evaluation():
    print("\n--- run_evaluation: Final evaluation with test patches ---")
    script = os.path.join(BENCH_DIR, 'run_evaluation.sh')
    result = subprocess.run(['/bin/bash', script, 'test'])
    if result.returncode != 0:
        print("ERROR: run_evaluation.sh test failed.", file=sys.stderr)
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="Gradle SWE-bench pipeline")
    parser.add_argument('--verdict',    default='correct', help="Filter by review verdict (default: 'correct').")
    parser.add_argument('--confidence', default='high',    help="Filter by confidence level (default: 'high').")
    args = parser.parse_args()

    def predicate(r):
        return r.get('verdict') == args.verdict and r.get('confidence') == args.confidence

    auto_steps = [
        functools.partial(filter_reviews, predicate=predicate),
        build_images,
        filter_failures,
    ]
    for step in auto_steps:
        step()
    print("\n--- Done: automatable steps complete ---")
    print("\nManual steps remaining:")
    print("  generate_patches : run the agent, save test-patch dataset")
    print("  run_evaluation   : /bin/bash gradle-bench/run_evaluation.sh test")


if __name__ == '__main__':
    main()

"""
Steps 3a & 3b: Analyze Docker build logs and filter out failed instances.

3a — analyze():        Scans logs/build_images/instances/<instance>/build_image.log
                       and produces build_analysis.json with per-instance status.
3b — filter_failures(): Reads build_analysis.json, removes failed instances from
                        gradle_benchmark_dataset_correct_high.json (in-place).
"""
import glob
import os
from filter import BENCH_DIR, DATA_DIR, load_json, save_json

LOGS_DIR = os.path.join(BENCH_DIR, 'logs', 'run_evaluation', 'gradle_benchmark_v0_build', 'gold')
BUILD_ANALYSIS = os.path.join(BENCH_DIR, 'build_analysis.json')
DATASET = os.path.join(DATA_DIR, 'gradle_benchmark_dataset_reviewed.json')


def analyze():
    """Step 3a: scan build logs and write build_analysis.json."""
    results = []
    instance_dirs = sorted(glob.glob(os.path.join(LOGS_DIR, '*')))
    for instance_dir in instance_dirs:
        instance = os.path.basename(instance_dir)
        log_path = os.path.join(instance_dir, 'run_instance.log')
        if not os.path.exists(log_path):
            continue
        with open(log_path) as f:
            content = f.read()
        if 'BUILD FAILED' in content or 'non-zero code' in content:
            error_line = next(
                (line.strip() for line in content.splitlines() if 'BUILD FAILED' in line or 'non-zero code' in line),
                'unknown error'
            )
            results.append({'instance': instance, 'status': 'failure', 'error': error_line})
        else:
            results.append({'instance': instance, 'status': 'success'})

    successes = sum(1 for r in results if r['status'] == 'success')
    failures = len(results) - successes
    print(f'Analyzed {len(results)} instances: {successes} success, {failures} failure')
    save_json(BUILD_ANALYSIS, results)
    return BUILD_ANALYSIS


def filter_failures():
    """Step 3b: remove failed instances from the dataset (in-place)."""
    analysis = load_json(BUILD_ANALYSIS)
    failed = {
        entry['instance']
        for entry in analysis
        if entry.get('status') == 'failure'
    }
    print(f'Failed instances from build: {len(failed)}')

    dataset = load_json(DATASET)
    before = len(dataset)
    filtered = [item for item in dataset if item.get('instance_id') not in failed]
    save_json(DATASET, filtered)
    print(f'Dataset: {before} → {len(filtered)} items (removed {before - len(filtered)})')
    return DATASET


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Build failure analysis and filtering")
    parser.add_argument('--mode', choices=['analyze', 'filter'], default='analyze',
                        help="analyze: scan logs → build_analysis.json; filter: remove failed from dataset")
    args = parser.parse_args()
    if args.mode == 'analyze':
        analyze()
    else:
        filter_failures()

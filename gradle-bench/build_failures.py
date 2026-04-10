"""
Steps 2a & 2b: Analyze Docker build logs and filter out failed instances.

2a — analyze():         Scans logs/build_images/instances/<instance>/build_image.log
                        and produces build_analysis.json with per-instance status.
2b — filter_failures(): Reads build_analysis.json and the raw dataset, writes
                        gradle_benchmark_dataset_buildable.json containing only
                        instances whose Docker image built successfully.
"""
import glob
import json
import os

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BENCH_DIR, 'data')
LOGS_DIR = os.path.join(BENCH_DIR, 'logs', 'build_images', 'instances')


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'Saved {len(data)} items → {path}')
BUILD_ANALYSIS = os.path.join(DATA_DIR, 'build_analysis.json')
INPUT_DATASET = os.path.join(DATA_DIR, 'gradle_benchmark_dataset.json')
OUTPUT_DATASET = os.path.join(DATA_DIR, 'gradle_benchmark_dataset_buildable.json')


def analyze():
    """Step 2a: scan build logs and write build_analysis.json."""
    results = []
    instance_dirs = sorted(glob.glob(os.path.join(LOGS_DIR, '*')))
    for instance_dir in instance_dirs:
        # Log dirs are named as Docker images: sweb.eval.{arch}.{instance_id}__{tag}
        # Extract the bare instance_id to match the dataset's instance_id field.
        dirname = os.path.basename(instance_dir)
        parts = dirname.split('.', 3)
        instance_id = parts[3].rsplit('__', 1)[0] if len(parts) == 4 else dirname

        log_path = os.path.join(instance_dir, 'build_image.log')
        if not os.path.exists(log_path):
            continue
        with open(log_path) as f:
            content = f.read()
        if 'BUILD FAILED' in content or 'non-zero code' in content:
            error_line = next(
                (line.strip() for line in content.splitlines() if 'BUILD FAILED' in line or 'non-zero code' in line),
                'unknown error'
            )
            results.append({'instance_id': instance_id, 'status': 'failure', 'error': error_line})
        else:
            results.append({'instance_id': instance_id, 'status': 'success'})

    successes = sum(1 for r in results if r['status'] == 'success')
    failures = len(results) - successes
    print(f'Analyzed {len(results)} instances: {successes} success, {failures} failure')
    save_json(BUILD_ANALYSIS, results)
    return BUILD_ANALYSIS


def filter_failures():
    """Step 2b: keep only successfully-built instances; write to OUTPUT_DATASET."""
    analysis = load_json(BUILD_ANALYSIS)
    successful = {
        entry['instance_id']
        for entry in analysis
        if entry.get('status') == 'success'
    }
    failed = len(analysis) - len(successful)
    print(f'Failed instances from build: {failed}')

    dataset = load_json(INPUT_DATASET)
    before = len(dataset)
    buildable = [item for item in dataset if item.get('instance_id') in successful]
    save_json(OUTPUT_DATASET, buildable)
    print(f'Dataset: {before} → {len(buildable)} buildable items (removed {before - len(buildable)})')
    return OUTPUT_DATASET


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

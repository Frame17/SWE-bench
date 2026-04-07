"""
Shared utilities and filtering functions for the Gradle SWE-bench pipeline.

Constants:
  BENCH_DIR, DATA_DIR, REPO_ROOT
  load_json, save_json, filter_dataset_by_ids

Step 1 — filter_by_review:
  Filters gradle_benchmark_dataset.json to instances with
  verdict=correct and confidence=high in gradle_bench_v0_reviews.json.

Utility — filter_by_resolved:
  Filters gradle_benchmark_dataset.json to resolved instances only,
  based on run_evaluation report.json files under logs/.
"""
import glob
import json
import os

BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BENCH_DIR, 'data')
REPO_ROOT = os.path.dirname(BENCH_DIR)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f'Saved {len(data)} items → {path}')


def filter_dataset_by_ids(dataset, approved_ids, id_key='instance_id'):
    """Return items from dataset whose id_key value is in approved_ids."""
    filtered = [item for item in dataset if item.get(id_key) in approved_ids]
    print(f'Total dataset items: {len(dataset)}')
    print(f'Approved IDs: {len(approved_ids)}')
    print(f'Matched items: {len(filtered)}')
    return filtered


def _default_review_predicate(r):
    return r.get('verdict') == 'correct' and r.get('confidence') == 'high'


def filter_by_review(predicate=None):
    if predicate is None:
        predicate = _default_review_predicate
    reviews = load_json(os.path.join(DATA_DIR, 'reviews.json'))
    dataset = load_json(os.path.join(DATA_DIR, 'gradle_benchmark_dataset.json'))

    approved_ids = {
        r['task_id']
        for r in reviews
        if predicate(r)
    }
    filtered = filter_dataset_by_ids(dataset, approved_ids)

    output = os.path.join(DATA_DIR, 'gradle_benchmark_dataset_reviewed.json')
    save_json(output, filtered)
    return output


def filter_by_resolved():
    resolved_ids = set()
    pattern = os.path.join(REPO_ROOT, 'logs/run_evaluation/gradle_benchmark_v0/gold/*/report.json')
    for path in glob.glob(pattern):
        for instance_id, info in load_json(path).items():
            if info.get('resolved', False):
                resolved_ids.add(instance_id)

    print(f'Resolved instances: {len(resolved_ids)}')

    dataset = load_json(os.path.join(DATA_DIR, 'gradle_benchmark_dataset.json'))
    filtered = filter_dataset_by_ids(dataset, resolved_ids)

    output = os.path.join(DATA_DIR, 'gradle_benchmark_dataset_filtered.json')
    save_json(output, filtered)
    return output


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Dataset filtering utilities")
    parser.add_argument('--mode', choices=['review', 'resolved'], default='review',
                        help="'review' = filter by human reviews (step 1); 'resolved' = filter by resolved instances")
    args = parser.parse_args()
    if args.mode == 'review':
        filter_by_review()
    else:
        filter_by_resolved()

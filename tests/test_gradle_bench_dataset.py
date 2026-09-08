import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRADLE_BENCH = ROOT / "gradle-bench"
NAMESPACE = "gradlebench"


def load_augment_module():
    path = GRADLE_BENCH / "augment_dataset.py"
    module_spec = importlib.util.spec_from_file_location("augment_dataset", path)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def test_representative_dataset_uses_gradlebench_namespace():
    dataset_path = (
        GRADLE_BENCH / "data" / "gradle_benchmark_dataset_representative_100.json"
    )
    dataset = json.loads(dataset_path.read_text())
    augment = load_augment_module()

    count = augment.augment_dataset(
        dataset,
        arch="x86_64",
        namespace=NAMESPACE,
        instance_image_tag="latest",
    )

    assert count == 100
    assert len(dataset) == 100
    assert all(item["image_name"].startswith(f"{NAMESPACE}/") for item in dataset)

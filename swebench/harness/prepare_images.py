import docker
import resource
import json
import os
import threading

from argparse import ArgumentParser

from swebench.harness.constants import KEY_INSTANCE_ID, LATEST
from swebench.harness.docker_build import build_instance_images
from swebench.harness.docker_utils import list_images
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.utils import load_swebench_dataset, str2bool, optional_str


def filter_dataset_to_build(
    dataset: list,
    instance_ids: list | None,
    client: docker.DockerClient,
    force_rebuild: bool,
    namespace: str = None,
    tag: str = None,
    env_image_tag: str = None,
):
    """
    Filter the dataset to only include instances that need to be built.

    Args:
        dataset (list): List of instances (usually all of SWE-bench dev/test split)
        instance_ids (list): List of instance IDs to build.
        client (docker.DockerClient): Docker client.
        force_rebuild (bool): Whether to force rebuild all images.
    """
    # Get existing images
    existing_images = list_images(client)
    data_to_build = []

    if instance_ids is None:
        instance_ids = [instance[KEY_INSTANCE_ID] for instance in dataset]

    # Check if all instance IDs are in the dataset
    not_in_dataset = set(instance_ids).difference(
        set([instance[KEY_INSTANCE_ID] for instance in dataset])
    )
    if not_in_dataset:
        raise ValueError(f"Instance IDs not found in dataset: {not_in_dataset}")

    for instance in dataset:
        if instance[KEY_INSTANCE_ID] not in instance_ids:
            # Skip instances not in the list
            continue

        # Check if the instance needs to be built (based on force_rebuild flag and existing images)
        spec = make_test_spec(
            instance,
            namespace=namespace,
            instance_image_tag=tag,
            env_image_tag=env_image_tag,
        )
        if force_rebuild:
            data_to_build.append(instance)
        elif spec.instance_image_key not in existing_images:
            data_to_build.append(instance)

    return data_to_build


def main(
    dataset_name,
    split,
    instance_ids,
    max_workers,
    force_rebuild,
    open_file_limit,
    namespace,
    tag,
    env_image_tag,
    cache_path=None,
):
    """
    Build Docker images for the specified instances.

    Args:
        instance_ids (list): List of instance IDs to build.
        max_workers (int): Number of workers for parallel processing.
        force_rebuild (bool): Whether to force rebuild all images.
        open_file_limit (int): Open file limit.
        cache_path (str): Path to a cache file to record build status.
    """
    # Set open file limit
    resource.setrlimit(resource.RLIMIT_NOFILE, (open_file_limit, open_file_limit))
    client = docker.from_env()

    # Snapshot the local Docker image tags once so the cache filter and
    # filter_dataset_to_build can both verify image presence without
    # repeatedly querying the daemon.
    existing_images = list_images(client)

    # Load cache
    cache = {}
    if cache_path and os.path.exists(cache_path):
        with open(cache_path) as f:
            cache = json.load(f)

    # Filter out instances that were not specified
    if instance_ids is not None and len(instance_ids) == 0:
        dataset = []
    else:
        dataset = load_swebench_dataset(dataset_name, split, instance_ids=instance_ids)

    # Filter based on cache:
    # - 'success' entries are skipped only when the corresponding image is
    #   actually present in the local Docker daemon. This guards against
    #   stale cache entries (e.g. after `docker image prune`) that would
    #   otherwise cause prepare_images to no-op while the image is missing.
    # - 'fail' (and any non-success) entries: skipped without force_rebuild,
    #   rebuilt with force_rebuild — same as before.
    # - Instances not in the cache: built unconditionally — same as before.
    if cache:
        original_count = len(dataset)
        kept = []
        stale_success = []  # cached 'success' entries whose image was missing
        for instance in dataset:
            iid = instance[KEY_INSTANCE_ID]
            status = cache.get(iid)
            if status == "success":
                spec = make_test_spec(
                    instance,
                    namespace=namespace,
                    instance_image_tag=tag,
                    env_image_tag=env_image_tag,
                )
                if spec.instance_image_key in existing_images:
                    print(f"  Found existing image: {spec.instance_image_key}")
                    continue  # skip — cache says success and image is present
                stale_success.append((iid, spec.instance_image_key))
                kept.append(instance)
            elif status is not None and not force_rebuild:
                # Cached failure (or any non-success) — skip unless forcing.
                continue
            else:
                # Not in cache, or in cache but force_rebuild — build it.
                kept.append(instance)
        dataset = kept
        skipped = original_count - len(dataset)
        if skipped:
            print(f"Skipping {skipped} instances found in build cache")
        if stale_success:
            print(
                f"Note: {len(stale_success)} cached 'success' entr"
                f"{'y' if len(stale_success) == 1 else 'ies'} reference "
                "image(s) missing from the local Docker daemon — will rebuild:"
            )
            for iid, key in stale_success[:10]:
                print(f"  {iid}  →  {key}")
            if len(stale_success) > 10:
                print(f"  ... and {len(stale_success) - 10} more")

    if len(dataset) == 0:
        print("All images exist. Nothing left to build.")
        return 0

    dataset = filter_dataset_to_build(
        dataset, instance_ids, client, force_rebuild, namespace, tag, env_image_tag
    )

    if len(dataset) == 0:
        print("All images exist. Nothing left to build.")
        return 0

    # Build a cache-writing callback so the file is updated after each image build
    on_complete = None
    if cache_path:
        cache_lock = threading.Lock()

        def on_complete(payload, success):
            spec = payload[0]
            with cache_lock:
                cache[spec.instance_id] = "success" if success else "fail"
                with open(cache_path, "w") as f:
                    json.dump(cache, f, indent=2)

    # Build images for remaining instances
    successful, failed = build_instance_images(
        client=client,
        dataset=dataset,
        force_rebuild=force_rebuild,
        max_workers=max_workers,
        namespace=namespace,
        tag=tag,
        env_image_tag=env_image_tag,
        on_complete=on_complete,
    )

    print(f"Successfully built {len(successful)} images")
    print(f"Failed to build {len(failed)} images")


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "--dataset_name",
        type=str,
        default="SWE-bench/SWE-bench_Lite",
        help="Name of the dataset to use",
    )
    parser.add_argument("--split", type=str, default="test", help="Split to use")
    parser.add_argument(
        "--instance_ids",
        nargs="+",
        type=str,
        help="Instance IDs to run (space separated)",
    )
    parser.add_argument(
        "--max_workers", type=int, default=4, help="Max workers for parallel processing"
    )
    parser.add_argument(
        "--force_rebuild", type=str2bool, default=False, help="Force rebuild images"
    )
    parser.add_argument(
        "--open_file_limit", type=int, default=8192, help="Open file limit"
    )
    parser.add_argument(
        "--namespace",
        type=optional_str,
        default=None,
        help="Namespace to use for the images (default: None)",
    )
    parser.add_argument(
        "--tag", type=str, default=LATEST, help="Tag to use for the images"
    )
    parser.add_argument(
        "--env_image_tag", type=str, default=LATEST, help="Environment image tag to use"
    )
    parser.add_argument(
        "--cache_path",
        type=str,
        default=None,
        help="Path to a cache file to record build status",
    )
    args = parser.parse_args()
    main(**vars(args))

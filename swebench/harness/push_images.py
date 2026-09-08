"""Publish successfully built SWE-bench instance images."""

from __future__ import annotations

import subprocess
import sys

import docker


def push_instance_images(
    client: docker.DockerClient,
    test_specs: list,
    cache: dict[str, str],
) -> list[str]:
    """Push selected successful instance images and return failed references."""
    failures: list[str] = []
    candidates: list[str] = []

    for spec in test_specs:
        image = spec.instance_image_key
        if not spec.is_remote_image:
            print(f"Cannot push unqualified image: {image}", file=sys.stderr)
            failures.append(image)
            continue
        if cache.get(spec.instance_id) != "success":
            print(
                f"Not pushing {image}: build is not marked successful",
                file=sys.stderr,
            )
            failures.append(image)
            continue
        try:
            client.images.get(image)
        except docker.errors.ImageNotFound:
            print(f"Not pushing {image}: image is missing locally", file=sys.stderr)
            failures.append(image)
            continue
        except docker.errors.DockerException as error:
            print(f"Cannot inspect {image}: {error}", file=sys.stderr)
            failures.append(image)
            continue
        candidates.append(image)

    push_failures = 0
    for index, image in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] Pushing {image}")
        try:
            result = subprocess.run(["docker", "push", image], check=False)
        except OSError as error:
            print(f"Failed to push {image}: {error}", file=sys.stderr)
            push_failures += 1
            failures.append(image)
            continue
        if result.returncode != 0:
            print(f"Failed to push {image}", file=sys.stderr)
            push_failures += 1
            failures.append(image)

    print(f"Pushed {len(candidates) - push_failures} image(s)")
    return failures

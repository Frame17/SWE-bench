from types import SimpleNamespace
from unittest.mock import MagicMock

import docker

from swebench.harness.push_images import push_instance_images


def spec(instance_id: str, image: str, remote: bool = True):
    return SimpleNamespace(
        instance_id=instance_id,
        instance_image_key=image,
        is_remote_image=remote,
    )


def test_pushes_only_successful_local_images(monkeypatch):
    first = spec("first", "gradlebench/first:latest")
    failed = spec("failed", "gradlebench/failed:latest")
    missing = spec("missing", "gradlebench/missing:latest")
    client = MagicMock()

    def get_image(image):
        if image == missing.instance_image_key:
            raise docker.errors.ImageNotFound(image)
        return MagicMock()

    client.images.get.side_effect = get_image
    run = MagicMock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr("swebench.harness.push_images.subprocess.run", run)

    failures = push_instance_images(
        client,
        [first, failed, missing],
        {"first": "success", "failed": "fail", "missing": "success"},
    )

    run.assert_called_once_with(
        ["docker", "push", first.instance_image_key], check=False
    )
    assert failures == [failed.instance_image_key, missing.instance_image_key]


def test_continues_after_push_failure(monkeypatch):
    first = spec("first", "gradlebench/first:latest")
    second = spec("second", "gradlebench/second:latest")
    client = MagicMock()
    run = MagicMock(
        side_effect=[
            SimpleNamespace(returncode=1),
            SimpleNamespace(returncode=0),
        ]
    )
    monkeypatch.setattr("swebench.harness.push_images.subprocess.run", run)

    failures = push_instance_images(
        client,
        [first, second],
        {"first": "success", "second": "success"},
    )

    assert run.call_count == 2
    assert failures == [first.instance_image_key]

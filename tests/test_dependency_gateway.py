from types import SimpleNamespace
from unittest.mock import MagicMock

from swebench.harness import docker_build
from swebench.harness.dependency_gateway import (
    DEPENDENCY_GATEWAY_HOSTS,
    add_dependency_gateway_cache_key,
    dependency_gateway_ca_pem,
    dependency_gateway_extra_hosts,
)
from swebench.harness.dockerfiles.kotlin import get_dependency_gateway_ca_install


PEM = """-----BEGIN CERTIFICATE-----
dGVzdA==
-----END CERTIFICATE-----
"""


def test_gateway_host_mappings(monkeypatch):
    monkeypatch.setenv("DEPENDENCY_GATEWAY", "host-gateway")

    assert dependency_gateway_extra_hosts() == {
        host: "host-gateway" for host in DEPENDENCY_GATEWAY_HOSTS
    }


def test_gateway_ca_changes_kotlin_cache_key(monkeypatch, tmp_path):
    certificate = tmp_path / "ca.crt"
    certificate.write_text(PEM)
    monkeypatch.setenv("DEPENDENCY_GATEWAY_CA_CERT", str(certificate))
    kotlin = SimpleNamespace(language="kotlin", docker_specs={})
    python = SimpleNamespace(language="py", docker_specs={})

    add_dependency_gateway_cache_key([kotlin, python])

    assert len(kotlin.docker_specs["dependency_gateway_ca_sha256"]) == 64
    assert kotlin.docker_specs["dependency_gateway_trust_version"] == "2"
    assert python.docker_specs == {}
    assert dependency_gateway_ca_pem() == PEM
    assert "JAVA_TOOL_OPTIONS" in get_dependency_gateway_ca_install()


def test_legacy_build_receives_gateway_hosts(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPENDENCY_GATEWAY", "host-gateway")
    monkeypatch.setattr(docker_build, "_is_cross_platform_build", lambda _: False)
    client = MagicMock()
    client.api.build.return_value = []

    docker_build.build_image(
        image_name="test-image:latest",
        setup_scripts={},
        dockerfile="FROM scratch\n",
        platform="linux/x86_64",
        client=client,
        build_dir=tmp_path,
    )

    assert client.api.build.call_args.kwargs["extra_hosts"] == {
        host: "host-gateway" for host in DEPENDENCY_GATEWAY_HOSTS
    }


def test_buildx_build_receives_gateway_hosts(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPENDENCY_GATEWAY", "host-gateway")
    monkeypatch.setattr(docker_build, "_is_cross_platform_build", lambda _: True)
    process = MagicMock(returncode=0)
    process.stdout = []
    popen = MagicMock(return_value=process)
    monkeypatch.setattr(docker_build.subprocess, "Popen", popen)
    client = MagicMock()

    docker_build.build_image(
        image_name="test-image:latest",
        setup_scripts={},
        dockerfile="FROM scratch\n",
        platform="linux/x86_64",
        client=client,
        build_dir=tmp_path,
    )

    command = popen.call_args.args[0]
    for host in DEPENDENCY_GATEWAY_HOSTS:
        position = command.index("--add-host", command.index("--tag") + 1)
        assert f"{host}=host-gateway" in command[position + 1 :]

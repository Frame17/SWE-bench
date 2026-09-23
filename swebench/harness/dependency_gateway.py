"""Configuration shared by dependency-gateway image builds."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path


DEPENDENCY_GATEWAY_HOSTS = (
    "repo.maven.apache.org",
    "repo1.maven.org",
    "plugins.gradle.org",
    "plugins-artifacts.gradle.org",
    "maven.reposilite.com",
)
DEPENDENCY_GATEWAY_TRUST_VERSION = "2"


def dependency_gateway_address() -> str | None:
    """Return the configured gateway address, or ``None`` when disabled."""
    address = os.environ.get("DEPENDENCY_GATEWAY")
    if not address:
        return None
    if any(char.isspace() for char in address) or any(
        char in address for char in ",/"
    ):
        raise ValueError(
            "DEPENDENCY_GATEWAY must be one address or host-gateway, "
            f"got: {address}"
        )
    return address


def dependency_gateway_extra_hosts() -> dict[str, str]:
    """Return Docker host mappings for every proxied dependency hostname."""
    address = dependency_gateway_address()
    if address is None:
        return {}
    return {host: address for host in DEPENDENCY_GATEWAY_HOSTS}


def dependency_gateway_ca_pem() -> str | None:
    """Read and validate the optional gateway CA certificate."""
    value = os.environ.get("DEPENDENCY_GATEWAY_CA_CERT")
    if not value:
        return None
    path = Path(value)
    if not path.is_file():
        raise FileNotFoundError(
            f"DEPENDENCY_GATEWAY_CA_CERT={value!r} does not name a regular file"
        )
    data = path.read_bytes()
    if b"-----BEGIN CERTIFICATE-----" not in data:
        raise ValueError(
            f"DEPENDENCY_GATEWAY_CA_CERT={value!r} is not a PEM certificate"
        )
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"DEPENDENCY_GATEWAY_CA_CERT={value!r} is not ASCII PEM data"
        ) from error


def add_dependency_gateway_cache_key(test_specs: list) -> None:
    """Include the gateway trust configuration in Kotlin intermediate keys."""
    pem = dependency_gateway_ca_pem()
    if pem is None:
        return
    digest = hashlib.sha256(pem.encode("ascii")).hexdigest()
    for spec in test_specs:
        if spec.language != "kotlin":
            continue
        spec.docker_specs["dependency_gateway_ca_sha256"] = digest
        spec.docker_specs["dependency_gateway_trust_version"] = (
            DEPENDENCY_GATEWAY_TRUST_VERSION
        )

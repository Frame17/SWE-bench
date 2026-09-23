import pytest

from swebench.harness.repo_customization.getodk__collect import SPECS as GETODK
from swebench.harness.repo_customization.google__ksp import SPECS as KSP
from swebench.harness.repo_customization.sqldelight__sqldelight import (
    SPECS as SQLDELIGHT,
)
from swebench.harness.repo_customization.wireapp__wire_android import SPECS as WIRE


@pytest.mark.parametrize("specs", [KSP, GETODK, WIRE, SQLDELIGHT])
def test_oracle_repairs_use_low_memory_root_tests(specs):
    spec = specs["1.0.0"]
    pre_install = "\n".join(spec["pre_install"])

    assert "org.gradle.jvmargs=-Xmx4g" in pre_install
    assert "kotlin.daemon.jvmargs=-Xmx3g" in pre_install
    assert '"org.gradle.workers.max=1"' in pre_install
    assert spec["test_cmd"] == ["chmod +x gradlew", "./gradlew test"]


def test_ksp_installs_libatomic():
    assert "libatomic1" in "\n".join(KSP["1.0.0"]["pre_install"])


def test_wire_keeps_recursive_submodule_initialization():
    assert any(
        "git submodule update --init --recursive" in command
        for command in WIRE["1.0.0"]["pre_install"]
    )


def test_sqldelight_keeps_kmp_browser_install():
    assert SQLDELIGHT["1.0.0"]["install"][-1] == "./gradlew assemble"

from swebench.harness.constants.jvm_base import (
    GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
    SPECS_JVM_LIBRARY_17,
)

REPO = "google/ksp"

_INSTALL_LIBATOMIC = (
    "apt-get update && "
    "apt-get install -y --no-install-recommends libatomic1 && "
    "rm -rf /var/lib/apt/lists/*"
)

# KSP's Gradle TestKit fixtures run the Kotlin/Wasm Node distribution, which
# requires libatomic.so.1. Smaller daemon heaps prevent the full root test suite
# from exhausting the evaluation container's memory.
SPECS = {
    "1.0.0": {
        **SPECS_JVM_LIBRARY_17["1.0.0"],
        "pre_install": [
            _INSTALL_LIBATOMIC,
            GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
            *SPECS_JVM_LIBRARY_17["1.0.0"]["pre_install"][1:],
        ],
    }
}

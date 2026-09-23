from swebench.harness.constants.jvm_base import (
    GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
    SPECS_ANDROID_17,
)

REPO = "getodk/collect"

# The root test suite exceeds the evaluation container's memory with the
# default Gradle and Kotlin daemon heaps.
SPECS = {
    "1.0.0": {
        **SPECS_ANDROID_17["1.0.0"],
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
            *SPECS_ANDROID_17["1.0.0"]["pre_install"][1:],
        ],
    }
}

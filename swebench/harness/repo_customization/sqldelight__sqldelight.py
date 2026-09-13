from swebench.harness.constants.jvm_base import (
    GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
    SPECS_JVM_LIBRARY_17_KMP_BROWSER,
)

REPO = "sqldelight/sqldelight"

# Keep the KMP/browser setup while reducing daemon memory for the root suite.
SPECS = {
    "1.0.0": {
        **SPECS_JVM_LIBRARY_17_KMP_BROWSER["1.0.0"],
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
            *SPECS_JVM_LIBRARY_17_KMP_BROWSER["1.0.0"]["pre_install"][1:],
        ],
    }
}

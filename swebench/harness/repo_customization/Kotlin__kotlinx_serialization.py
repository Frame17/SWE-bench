from swebench.harness.constants.kotlin_base import SPECS_KOTLIN_LIBRARY

# kover verification tasks must be excluded from both build and test.
SPECS = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew build -x test -x koverVerify -x koverCachedVerify -x koverVerifyHocon",
        ],
        "test_cmd": [
            "chmod +x gradlew",
            "./gradlew test -x koverVerify -x koverCachedVerify -x koverVerifyHocon",
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

from swebench.harness.constants.kotlin_base import SPECS_KOTLIN_ANDROID

# Dependency verification fails for several JitPack/GitHub artifacts whose checksums
# drifted from the committed verification-metadata.xml.
# Disable verification for both the install step and tests.
SPECS = {
    "1.0.0": {
        **SPECS_KOTLIN_ANDROID["1.0.0"],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assembleDebug --dependency-verification=off -Pandroid.base.ignoreExtraTranslations=true -Pandroid.lintOptions.abortOnError=false",
        ],
        "test_cmd": [
            "chmod +x gradlew",
            "./gradlew test --dependency-verification=off",
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

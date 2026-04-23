from swebench.harness.constants.kotlin_base import SPECS_KOTLIN_LIBRARY

# Exposed starts Docker containers (MariaDB, MySQL, Postgres) for integration
# tests inside the Gradle build.  Docker-in-Docker is unavailable in our images.
SPECS = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assemble",
        ],
        "test_cmd": [
            "chmod +x gradlew",
            "./gradlew test -x mariadbComposeBuild -x mariadbComposeUp -x mysqlComposeBuild -x mysqlComposeUp -x postgresComposeBuild -x postgresComposeUp -x oracleComposeBuild -x oracleComposeUp -x sqlserverComposeBuild -x sqlserverComposeUp",
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

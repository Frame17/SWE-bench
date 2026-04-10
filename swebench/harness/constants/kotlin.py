# --add-exports and --add-opens flags required for KAPT compatibility with JDK 17+.
# KAPT accesses internal javac APIs (com.sun.tools.javac.*) which are encapsulated
# by the Java module system starting in JDK 17. Without these, KAPT tasks fail with:
#   IllegalAccessError: module jdk.compiler does not export com.sun.tools.javac.util
# --add-exports: allows direct access to the package's public types
# --add-opens:   additionally allows deep reflective access
_KAPT_JAVAC_PACKAGES = [
    "com.sun.tools.javac.api",
    "com.sun.tools.javac.code",
    "com.sun.tools.javac.comp",
    "com.sun.tools.javac.file",
    "com.sun.tools.javac.jvm",
    "com.sun.tools.javac.main",
    "com.sun.tools.javac.model",
    "com.sun.tools.javac.parser",
    "com.sun.tools.javac.processing",
    "com.sun.tools.javac.tree",
    "com.sun.tools.javac.util",
]

# Additional JDK internal packages needed by the Kotlin compiler itself
# (not just KAPT). FileChannelUtil needs sun.nio.ch.FileChannelImpl.
_KOTLIN_JDK_PACKAGES = [
    ("java.base", "sun.nio.ch"),
]

_KAPT_MODULE_FLAGS = " ".join(
    [
        f"--add-exports=jdk.compiler/{pkg}=ALL-UNNAMED "
        f"--add-opens=jdk.compiler/{pkg}=ALL-UNNAMED"
        for pkg in _KAPT_JAVAC_PACKAGES
    ]
    + [
        f"--add-exports={mod}/{pkg}=ALL-UNNAMED --add-opens={mod}/{pkg}=ALL-UNNAMED"
        for mod, pkg in _KOTLIN_JDK_PACKAGES
    ]
)

# Script that (re-)creates /root/.gradle/gradle.properties with the KAPT
# module-access flags.  This runs inside setup_repo.sh so it executes during
# the *instance* image build — which is always freshly built — rather than
# relying on a potentially stale/cached env image layer.
# Memory notes: the Gradle daemon and Kotlin daemon each run as separate JVMs.
# With both at -Xmx12g the combined footprint (~26 GB) easily exceeds typical
# Docker container memory limits and the OOM killer terminates the daemon
# ("Gradle build daemon disappeared unexpectedly").  6 GB each + 512 MB
# metaspace keeps the combined ceiling around 14 GB, which fits most build
# hosts while still being ample for KAPT / native / desugar workloads.
# workers.max=2 reduces parallel task memory pressure further.
GRADLE_PROPERTIES_SCRIPT = (
    "mkdir -p /root/.gradle && "
    'printf "%s\\n"'
    ' "org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=1g -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    ' "org.gradle.java.installations.auto-detect=true"'
    ' "org.gradle.java.installations.auto-download=true"'
    ' "org.gradle.caching=true"'
    ' "org.gradle.parallel=true"'
    ' "org.gradle.workers.max=2"'
    ' "org.gradle.vfs.watch=false"'
    ' "kotlin.daemon.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=512m -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    " > /root/.gradle/gradle.properties"
)

# Smaller heaps for a few very large Kotlin/JVM builds that were OOM-killed (exit 137) in
# gradle-bench image builds. Scoped to those repos only — not a global behavior change.
GRADLE_PROPERTIES_SCRIPT_LOW_MEM = (
    "mkdir -p /root/.gradle && "
    'printf "%s\\n"'
    ' "org.gradle.jvmargs=-Xmx4g -XX:MaxMetaspaceSize=768m -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    ' "org.gradle.java.installations.auto-detect=true"'
    ' "org.gradle.java.installations.auto-download=true"'
    ' "org.gradle.caching=true"'
    ' "org.gradle.parallel=true"'
    ' "org.gradle.workers.max=1"'
    ' "org.gradle.vfs.watch=false"'
    ' "kotlin.daemon.jvmargs=-Xmx3g -XX:MaxMetaspaceSize=384m -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    " > /root/.gradle/gradle.properties"
)

# pinterest/ktlint :build-logic requires a Java 24+ toolchain (see gradle-bench logs).
# Installed via openjdk-24-jdk-headless in the Dockerfile; Ubuntu names it java-24-openjdk-<arch>.
_GRADLE_JAVA24_HOME = "/usr/lib/jvm/java-24-openjdk-amd64"

# slackhq/circuit requires JDK 23 toolchain. Installed as Eclipse Temurin 23 in the Dockerfile.
_GRADLE_JAVA23_HOME = "/usr/lib/jvm/temurin-23-jdk"

GRADLE_PROPERTIES_SCRIPT_KTLINT = (
    "mkdir -p /root/.gradle && "
    'printf "%s\\n"'
    f' "org.gradle.java.home={_GRADLE_JAVA24_HOME}"'
    ' "org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=1g -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    ' "org.gradle.java.installations.auto-detect=true"'
    ' "org.gradle.java.installations.auto-download=true"'
    ' "org.gradle.caching=true"'
    ' "org.gradle.parallel=true"'
    ' "org.gradle.workers.max=2"'
    ' "org.gradle.vfs.watch=false"'
    ' "kotlin.daemon.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=512m -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    " > /root/.gradle/gradle.properties"
)

KOTLIN_LOGS_COLLECTOR_SCRIPT = r"""cat > /root/kotlin_logs_collector.sh << 'KOTLIN_LOGS_EOF'
#!/usr/bin/env bash

set -euo pipefail

ROOT="."
OUTPUT_FILE="reports/junit/all-testsuites.xml"

usage() {
  cat <<'EOF'
Usage: kotlin_logs_collector.sh [options]

Options:
  -r, --root DIR       Repository root to search for JUnit XML (default .)
  -o, --output FILE    Path for merged all-testsuites.xml (default reports/junit/all-testsuites.xml)
  -h, --help           Show help

Example:
  ./kotlin_logs_collector.sh --root detekt --output artifacts_jb/junit/all-testsuites.xml
EOF
}

# ---------- Argument parsing ----------
while [ $# -gt 0 ]; do
  case "$1" in
    -r|--root)
      ROOT="$2"; shift 2 ;;
    -o|--output)
      OUTPUT_FILE="$2"; shift 2 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1 ;;
  esac
done

ROOT_DIR="$(cd "$ROOT" && pwd)"

MERGED_PATH="$OUTPUT_FILE"
mkdir -p "$(dirname "$MERGED_PATH")"


mapfile -t junit_files < <(
  cd "$ROOT_DIR" && find . -type f -path '*/build/test-results/*/TEST*.xml'
)

if [ ${#junit_files[@]} -eq 0 ]; then
  echo "No JUnit XML files found"
  {
    printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>'
    printf '%s\n' '<testsuites>'
    printf '%s\n' '</testsuites>'
  } > "$MERGED_PATH"
  exit 0
fi

{
  printf '%s\n' '<?xml version="1.0" encoding="UTF-8"?>'
  printf '%s\n' '<testsuites>'

  for rel in "${junit_files[@]}"; do
    rel="${rel#./}"
    file="$ROOT_DIR/$rel"
#    printf '<!-- %s -->\n' "$rel"

    skip=1
    while IFS= read -r line; do
      if [ $skip -eq 1 ] && [[ $line =~ ^\<\?xml ]]; then
        continue
      fi
      skip=0
      printf '%s\n' "$line"
    done < "$file"
  done

  printf '%s\n' '</testsuites>'
} > "$MERGED_PATH"

echo "Merged ${#junit_files[@]} files → $MERGED_PATH"
KOTLIN_LOGS_EOF
"""

STATIC_VERIFICATION_SCRIPT = r"""cat > /root/static_verification.sh << 'STATIC_VERIFICATION_EOF'
#!/usr/bin/env bash

set -euo pipefail

./gradlew tasks

echo "STATIC VERIFICATION SUCCESS"
STATIC_VERIFICATION_EOF
"""

# InsertKoinIO/koin keeps the Gradle wrapper under projects/ (no root gradlew).
STATIC_VERIFICATION_KOIN_SCRIPT = r"""cat > /root/static_verification.sh << 'STATIC_VERIFICATION_KOIN_EOF'
#!/usr/bin/env bash

set -euo pipefail

cd projects
./gradlew tasks

echo "STATIC VERIFICATION SUCCESS"
STATIC_VERIFICATION_KOIN_EOF
"""

STATIC_VERIFICATION_KTLINT_SCRIPT = r"""cat > /root/static_verification.sh << 'STATIC_VERIFICATION_KTLINT_EOF'
#!/usr/bin/env bash

set -euo pipefail

export JAVA_HOME=""" + _GRADLE_JAVA24_HOME + r"""
export PATH="${JAVA_HOME}/bin:${PATH}"
./gradlew tasks

echo "STATIC VERIFICATION SUCCESS"
STATIC_VERIFICATION_KTLINT_EOF
"""

SPECS_KOTLIN_LIBRARY = {
    "1.0.0": {
        "docker_specs": {"java_version": "17"},
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT,
            KOTLIN_LOGS_COLLECTOR_SCRIPT,
            "chmod +x /root/kotlin_logs_collector.sh",
            STATIC_VERIFICATION_SCRIPT,
            "chmod +x /root/static_verification.sh",
        ],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew build -x test",
        ],
        "test_cmd": [
            "chmod +x gradlew",
            "./gradlew test",
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

SPECS_KOTLIN_LIBRARY_SERIALIZATION = {
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

SPECS_KOTLIN_LIBRARY_KTLINT = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "pre_install": [
            f'export JAVA_HOME={_GRADLE_JAVA24_HOME} && export PATH="$JAVA_HOME/bin:$PATH"',
            GRADLE_PROPERTIES_SCRIPT_KTLINT,
            KOTLIN_LOGS_COLLECTOR_SCRIPT,
            "chmod +x /root/kotlin_logs_collector.sh",
            STATIC_VERIFICATION_KTLINT_SCRIPT,
            "chmod +x /root/static_verification.sh",
        ],
        "install": [
            f'export JAVA_HOME={_GRADLE_JAVA24_HOME} && export PATH="$JAVA_HOME/bin:$PATH" && chmod +x gradlew',
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== JAVA_HOME ===' && echo \"JAVA_HOME=${JAVA_HOME:-not set}\" && java -version 2>&1 | head -1 && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew build -x test",
        ],
        "test_cmd": [
            f'export JAVA_HOME={_GRADLE_JAVA24_HOME} && export PATH="$JAVA_HOME/bin:$PATH" && chmod +x gradlew',
            f'export JAVA_HOME={_GRADLE_JAVA24_HOME} && export PATH="$JAVA_HOME/bin:$PATH" && ./gradlew test',
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

SPECS_KOTLIN_LIBRARY_LOW_MEM = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
            *SPECS_KOTLIN_LIBRARY["1.0.0"]["pre_install"][1:],
        ],
    }
}

SPECS_KOTLIN_LIBRARY_KOIN = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT,
            KOTLIN_LOGS_COLLECTOR_SCRIPT,
            "chmod +x /root/kotlin_logs_collector.sh",
            STATIC_VERIFICATION_KOIN_SCRIPT,
            "chmod +x /root/static_verification.sh",
        ],
        "install": [
            "cd projects",
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assemble",
        ],
        "test_cmd": [
            "cd projects && chmod +x gradlew",
            "cd projects && ./gradlew test",
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

SPECS_KOTLIN_ANDROID = {
    "1.0.0": {
        "docker_specs": {"java_version": "17"},
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT,
            KOTLIN_LOGS_COLLECTOR_SCRIPT,
            "chmod +x /root/kotlin_logs_collector.sh",
            STATIC_VERIFICATION_SCRIPT,
            "chmod +x /root/static_verification.sh",
            "mkdir -p ~/.android && touch ~/.android/repositories.cfg",
            'rm -f debug.keystore && keytool -genkey -v -keystore debug.keystore -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"',
        ],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assembleDebug -Pandroid.base.ignoreExtraTranslations=true -Pandroid.lintOptions.abortOnError=false",
        ],
        "test_cmd": [
            "chmod +x gradlew",
            "./gradlew test",
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

SPECS_KOTLIN_ANDROID_21 = {
    "1.0.0": {
        "docker_specs": {"java_version": "21"},
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT,
            KOTLIN_LOGS_COLLECTOR_SCRIPT,
            "chmod +x /root/kotlin_logs_collector.sh",
            STATIC_VERIFICATION_SCRIPT,
            "chmod +x /root/static_verification.sh",
            "mkdir -p ~/.android && touch ~/.android/repositories.cfg",
            'rm -f debug.keystore && keytool -genkey -v -keystore debug.keystore -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Android Debug,O=Android,C=US"',
        ],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assembleDebug -Pandroid.base.ignoreExtraTranslations=true -Pandroid.lintOptions.abortOnError=false",
        ],
        "test_cmd": [
            "chmod +x gradlew",
            "./gradlew test",
            "/bin/bash /root/static_verification.sh",
            "/bin/bash /root/kotlin_logs_collector.sh",
            "cat /testbed/reports/junit/all-testsuites.xml",
        ],
    }
}

# Repos that use older Kotlin/Native versions (< 1.8) which don't ship
# linux-aarch64 prebuilt binaries. These must be built under x86_64 even on
# ARM hosts (Docker will use QEMU emulation automatically).
SPECS_KOTLIN_ANDROID_X86 = {
    "1.0.0": {
        **SPECS_KOTLIN_ANDROID["1.0.0"],
        "docker_specs": {
            **SPECS_KOTLIN_ANDROID["1.0.0"]["docker_specs"],
            "arch": "x86_64",
        },
    }
}

# kotest, sqldelight, ktor — Kotlin Multiplatform projects whose `build` triggers
# JS/Wasm browser tests that fail without a headless Chrome.  Use `assemble` in the
# install step to avoid running tests, and skip browser test tasks in test_cmd.
SPECS_KOTLIN_LIBRARY_KMP_BROWSER = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assemble",
        ],
    }
}

# JetBrains/Exposed starts Docker containers (MariaDB, MySQL, Postgres) for integration
# tests inside the Gradle build.  Docker-in-Docker is unavailable in our images.
SPECS_KOTLIN_LIBRARY_EXPOSED = {
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

# slackhq/circuit requires JDK 23 toolchain.  Tell Gradle where to find JDK 23 (Temurin)
# and JDK 24 (openjdk-24 from apt) so it can auto-detect them.
GRADLE_PROPERTIES_SCRIPT_CIRCUIT = (
    "mkdir -p /root/.gradle && "
    'printf "%s\\n"'
    ' "org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=1g -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    f' "org.gradle.java.installations.paths={_GRADLE_JAVA23_HOME},{_GRADLE_JAVA24_HOME}"'
    ' "org.gradle.java.installations.auto-detect=true"'
    ' "org.gradle.java.installations.auto-download=false"'
    ' "org.gradle.caching=true"'
    ' "org.gradle.parallel=true"'
    ' "org.gradle.workers.max=2"'
    ' "org.gradle.vfs.watch=false"'
    ' "kotlin.daemon.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=512m -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    " > /root/.gradle/gradle.properties"
)

SPECS_KOTLIN_LIBRARY_CIRCUIT = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT_CIRCUIT,
            *SPECS_KOTLIN_LIBRARY["1.0.0"]["pre_install"][1:],
        ],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assemble",
        ],
    }
}

# ReVanced/revanced-manager needs gpr.user and gpr.key properties set (GitHub Packages auth).
# We inject dummy values so the settings.gradle.kts doesn't crash on missing extra properties.
GRADLE_PROPERTIES_SCRIPT_REVANCED = (
    "mkdir -p /root/.gradle && "
    'printf "%s\\n"'
    ' "org.gradle.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=1g -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    ' "org.gradle.java.installations.auto-detect=true"'
    ' "org.gradle.java.installations.auto-download=true"'
    ' "org.gradle.caching=true"'
    ' "org.gradle.parallel=true"'
    ' "org.gradle.workers.max=2"'
    ' "org.gradle.vfs.watch=false"'
    ' "kotlin.daemon.jvmargs=-Xmx6g -XX:MaxMetaspaceSize=512m -XX:+HeapDumpOnOutOfMemoryError '
    + _KAPT_MODULE_FLAGS
    + '"'
    ' "gpr.user=nobody"'
    ' "gpr.key=none"'
    " > /root/.gradle/gradle.properties"
)

SPECS_KOTLIN_ANDROID_REVANCED = {
    "1.0.0": {
        **SPECS_KOTLIN_ANDROID["1.0.0"],
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT_REVANCED,
            *SPECS_KOTLIN_ANDROID["1.0.0"]["pre_install"][1:],
        ],
    }
}

# arrow-kt/arrow: `build` triggers animalsnifferAndroidMain (missing androidMainClasses task),
# kotlinStoreYarnLock (stale lock), and OOM on large multiplatform builds.
# `assemble` skips all check-phase tasks.  Low-mem to avoid OOM.
SPECS_KOTLIN_LIBRARY_ARROW = {
    "1.0.0": {
        **SPECS_KOTLIN_LIBRARY["1.0.0"],
        "pre_install": [
            GRADLE_PROPERTIES_SCRIPT_LOW_MEM,
            *SPECS_KOTLIN_LIBRARY["1.0.0"]["pre_install"][1:],
        ],
        "install": [
            "chmod +x gradlew",
            "echo '=== GRADLE_USER_HOME ===' && echo \"GRADLE_USER_HOME=${GRADLE_USER_HOME:-not set}\" && echo '=== gradle.properties ===' && cat ${GRADLE_USER_HOME:-/root/.gradle}/gradle.properties && echo '=== END gradle.properties ==='",
            "./gradlew assemble",
        ],
    }
}

# nextcloud/talk-android: dependency verification fails for several JitPack/GitHub artifacts
# whose checksums drifted from the committed verification-metadata.xml.
# Disable verification for the install step; tests will also need it.
SPECS_KOTLIN_ANDROID_TALK = {
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

# wireapp/wire-android: the repo uses a `kalium` git submodule that must be initialized
# after clone.  3/12 instances also have bad base_commit SHAs that can't be fixed here.
SPECS_KOTLIN_ANDROID_WIRE = {
    "1.0.0": {
        **SPECS_KOTLIN_ANDROID["1.0.0"],
        "pre_install": [
            "git submodule update --init --recursive || true",
            *SPECS_KOTLIN_ANDROID["1.0.0"]["pre_install"],
        ],
    }
}

MAP_REPO_VERSION_TO_SPECS_KOTLIN = {
    **{
        repo: SPECS_KOTLIN_ANDROID_21
        for repo in [
            "DroidKaigi/conference-app-2024",
            "MMRLApp/MMRL",
            "NordicSemiconductor/Android-DFU-Library",
            "Stypox/dicio-android",
            "T8RIN/ImageToolbox",
            "jarnedemeulemeester/findroid",
            "nextcloud/android",
            "thunderbird/thunderbird-android",
            "accrescent/accrescent",
            "stripe/stripe-android",
        ]
    },
    **{
        repo: SPECS_KOTLIN_ANDROID
        for repo in [
            "Aliucord/Aliucord",
            "AllanWang/Frost-for-Facebook",
            "AppIntro/AppIntro",
            "Automattic/pocket-casts-android",
            "GetStream/whatsApp-clone-compose",
            "GrapheneOS/Camera",
            "HabitRPG/habitica-android",
            "IacobIonut01/Gallery",
            "LemmyNet/jerboa",
            "LibChecker/LibChecker",
            "Mahmud0808/ColorBlendr",
            "MohamedRejeb/Compose-Rich-Editor",
            "NordicSemiconductor/Android-nRF-Toolbox",
            "Pool-Of-Tears/GreenStash",
            "Pool-Of-Tears/Myne",
            "RikkaApps/Shizuku",
            "Tapadoo/Alerter",
            "TrianguloY/URLCheck",
            "android/nowinandroid",
            "android/socialite",
            "android/sunflower",
            "android/uamp",
            "aniyomiorg/aniyomi",
            "avluis/Hentoid",
            "beemdevelopment/Aegis",
            "d4rken-org/capod",
            "element-hq/element-android",
            "flipperdevices/Flipper-Android-App",
            "getodk/collect",
            "iSoron/uhabits",
            "jaredsburrows/android-gradle-java-app-template",
            "keymapperorg/KeyMapper",
            "kylecorry31/Trail-Sense",
            "leonlatsch/Photok",
            "mihonapp/mihon",
            "nextcloud/notes-android",
            "owncloud/android",
            "oxygen-updater/oxygen-updater",
            "patzly/grocy-android",
            "recloudstream/cloudstream",
            "spacecowboy/Feeder",
            "tasks/tasks",
            "wikimedia/apps-android-wikipedia",
            "you-apps/ClockYou",
            "you-apps/RecordYou",
        ]
    },
    # Repos that use Kotlin/Native (e.g. Kotlin Multiplatform with iOS targets)
    # with Kotlin versions < 1.8 that lack linux-aarch64 prebuilt binaries.
    # These must build under x86_64 (QEMU emulation on ARM hosts).
    **{
        repo: SPECS_KOTLIN_ANDROID_X86
        for repo in [
            "DroidKaigi/conference-app-2021",
            "DroidKaigi/conference-app-2022",
            "DroidKaigi/conference-app-2023",
            "Shabinder/SpotiFlyer",
            "kasem-sm/SlimeKT",
        ]
    },
    # Pure Kotlin/JVM/multiplatform libraries — no Android app module,
    # install compiles sources without running tests.
    **{
        repo: SPECS_KOTLIN_LIBRARY_LOW_MEM
        for repo in [
            "Kotlin/dokka",
            "Kotlin/kotlinx.coroutines",
        ]
    },
    **{"InsertKoinIO/koin": SPECS_KOTLIN_LIBRARY_KOIN},
    **{"pinterest/ktlint": SPECS_KOTLIN_LIBRARY_KTLINT},
    **{"Kotlin/kotlinx.serialization": SPECS_KOTLIN_LIBRARY_SERIALIZATION},
    **{"JetBrains/Exposed": SPECS_KOTLIN_LIBRARY_EXPOSED},
    **{"slackhq/circuit": SPECS_KOTLIN_LIBRARY_CIRCUIT},
    **{"ReVanced/revanced-manager": SPECS_KOTLIN_ANDROID_REVANCED},
    **{
        repo: SPECS_KOTLIN_LIBRARY_KMP_BROWSER
        for repo in [
            "kotest/kotest",
            "ktorio/ktor",
            "sqldelight/sqldelight",
        ]
    },
    **{"arrow-kt/arrow": SPECS_KOTLIN_LIBRARY_ARROW},
    **{"nextcloud/talk-android": SPECS_KOTLIN_ANDROID_TALK},
    **{"wireapp/wire-android": SPECS_KOTLIN_ANDROID_WIRE},
    **{
        repo: SPECS_KOTLIN_LIBRARY
        for repo in [
            "JetBrains/compose-multiplatform",
            "ReactiveX/RxKotlin",
            "detekt/detekt",
            "google/ksp",
        ]
    },
}

MAP_REPO_TO_INSTALL_KOTLIN = {
    repo: f"git clone https://github.com/{repo}.git"
    for repo in MAP_REPO_VERSION_TO_SPECS_KOTLIN.keys()
}

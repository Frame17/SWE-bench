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

SPECS_KOTLIN_ANDROID = {
    "1.0.0": {
        "docker_specs": {"java_version": "17"},
        "pre_install": [
            KOTLIN_LOGS_COLLECTOR_SCRIPT,
            "chmod +x /root/kotlin_logs_collector.sh",
            STATIC_VERIFICATION_SCRIPT,
            "chmod +x /root/static_verification.sh",
            "mkdir -p ~/.android && touch ~/.android/repositories.cfg",
            "mkdir -p app/ && echo '{}' > app/google-services.json",
            "mkdir -p core/settings/ && echo '{}' > core/settings/google-services.json",
            "keytool -genkey -v -keystore debug.keystore -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname \"CN=Android Debug,O=Android,C=US\""
        ],
        "install": ["chmod +x gradlew", "./gradlew assemble --no-watch-fs -Dorg.gradle.jvmargs=\"-Xmx20g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8\" -Pandroid.base.ignoreExtraTranslations=true -Pandroid.lintOptions.abortOnError=false || ./gradlew assembleDebug --no-watch-fs -Pandroid.base.ignoreExtraTranslations=true -Pandroid.lintOptions.abortOnError=false"],
        "test_cmd": ["chmod +x gradlew", "./gradlew test --no-watch-fs -Dorg.gradle.jvmargs=\"-Xmx20g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8\"", "/bin/bash /root/static_verification.sh", "/bin/bash /root/kotlin_logs_collector.sh",
                     "cat /testbed/reports/junit/all-testsuites.xml"]}
}

SPECS_KOTLIN_ANDROID_21 = {
    "1.0.0": {
        "docker_specs": {"java_version": "21"},
        "pre_install": [
            KOTLIN_LOGS_COLLECTOR_SCRIPT,
            "chmod +x /root/kotlin_logs_collector.sh",
            STATIC_VERIFICATION_SCRIPT,
            "chmod +x /root/static_verification.sh",
            "mkdir -p ~/.android && touch ~/.android/repositories.cfg",
            "mkdir -p app/ && echo '{}' > app/google-services.json",
            "keytool -genkey -v -keystore debug.keystore -storepass android -alias androiddebugkey -keypass android -keyalg RSA -keysize 2048 -validity 10000 -dname \"CN=Android Debug,O=Android,C=US\""
        ],
        "install": ["chmod +x gradlew", "./gradlew assemble --no-watch-fs -Dorg.gradle.jvmargs=\"-Xmx20g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8\" -Pandroid.base.ignoreExtraTranslations=true -Pandroid.lintOptions.abortOnError=false || ./gradlew assembleDebug --no-watch-fs -Pandroid.base.ignoreExtraTranslations=true -Pandroid.lintOptions.abortOnError=false"],
        "test_cmd": ["chmod +x gradlew", "./gradlew test --no-watch-fs -Dorg.gradle.jvmargs=\"-Xmx20g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8\"", "/bin/bash /root/static_verification.sh", "/bin/bash /root/kotlin_logs_collector.sh",
                     "cat /testbed/reports/junit/all-testsuites.xml"]}
}

MAP_REPO_VERSION_TO_SPECS_KOTLIN = {
    **{
        repo: SPECS_KOTLIN_ANDROID_21
        for repo in [
            "android/nowinandroid",
            "thunderbird/thunderbird-android",
        ]
    },
    **{
        repo: SPECS_KOTLIN_ANDROID
        for repo in [
            "Aliucord/Aliucord",
            "AllanWang/Frost-for-Facebook",
            "AppIntro/AppIntro",
            "DroidKaigi/conference-app-2021",
            "DroidKaigi/conference-app-2023",
            "GetStream/whatsApp-clone-compose",
            "GrapheneOS/Camera",
            "IacobIonut01/Gallery",
            "LemmyNet/jerboa",
            "LibChecker/LibChecker",
            "MMRLApp/MMRL",
            "Mahmud0808/ColorBlendr",
            "NordicSemiconductor/Android-DFU-Library",
            "Pool-Of-Tears/GreenStash",
            "Pool-Of-Tears/Myne",
            "Shabinder/SpotiFlyer",
            "Stypox/dicio-android",
            "T8RIN/ImageToolbox",
            "Tapadoo/Alerter",
            "TrianguloY/URLCheck",
            "android/socialite",
            "android/sunflower",
            "android/uamp",
            "aniyomiorg/aniyomi",
            "avluis/Hentoid",
            "beemdevelopment/Aegis",
            "d4rken-org/capod",
            "flipperdevices/Flipper-Android-App",
            "getodk/collect",
            "iSoron/uhabits",
            "jaredsburrows/android-gradle-java-app-template",
            "jarnedemeulemeester/findroid",
            "kasem-sm/SlimeKT",
            "keymapperorg/KeyMapper",
            "kylecorry31/Trail-Sense",
            "leonlatsch/Photok",
            "nextcloud/android",
            "nextcloud/notes-android",
            "owncloud/android",
            "oxygen-updater/oxygen-updater",
            "patzly/grocy-android",
            "recloudstream/cloudstream",
            "spacecowboy/Feeder",
            "wikimedia/apps-android-wikipedia",
            "you-apps/ClockYou",
            "you-apps/RecordYou"
        ]
    }
}

MAP_REPO_TO_INSTALL_KOTLIN = {
    repo: f"git clone https://github.com/{repo}.git"
    for repo in MAP_REPO_VERSION_TO_SPECS_KOTLIN.keys()
}

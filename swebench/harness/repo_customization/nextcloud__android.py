"""Build the deleted JitPack android-library dependency from source."""

REPO = "nextcloud/android"

_ANDROID_LIBRARY_COMMIT = "291f9f3de673ca622999b0cedbd957ee6f0a31f8"

_ENABLE_MAVEN_LOCAL = r"""mkdir -p /root/.gradle/init.d
printf '\norg.gradle.dependency.verification=lenient\n' >> /root/.gradle/gradle.properties
cat > /root/.gradle/init.d/gradlebench-maven-local.gradle << 'GRADLEBENCH_MAVEN_LOCAL_EOF'
beforeSettings { settings ->
    settings.dependencyResolutionManagement.repositories {
        mavenLocal()
    }
}
GRADLEBENCH_MAVEN_LOCAL_EOF
"""

COMMANDS = [
    _ENABLE_MAVEN_LOCAL,
    "git clone --filter=blob:none https://github.com/nextcloud/android-library.git /tmp/gradlebench-android-library",
    "cd /tmp/gradlebench-android-library",
    f"git checkout {_ANDROID_LIBRARY_COMMIT}",
    "sed -i \"s/groupId = 'com.nextcloud.android-library'/groupId = 'com.github.nextcloud'/; s/artifactId = 'master'/artifactId = 'android-library'/\" library/build.gradle",
    "chmod +x gradlew",
    f"./gradlew --no-daemon -Pversion={_ANDROID_LIBRARY_COMMIT} :library:publishReleasePublicationToMavenLocal",
    "cd /testbed",
    "rm -rf /tmp/gradlebench-android-library",
]

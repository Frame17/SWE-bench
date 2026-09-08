"""Build deleted JitPack dependencies for Nextcloud Notes from source."""

REPO = "nextcloud/notes-android"

_ANDROID_LIBRARY_COMMIT = "a9732515be7fab2b8ab8523485df94782061d56a"
_ANDROID_COMMON_COMMIT = "4fc0f29981"
_ANDROID_COMMON_FULL_COMMIT = "4fc0f29981eee00251255f9ce704fbea4e008c45"

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

_ENABLE_PROJECT_MAVEN_LOCAL = r"""cat > /root/.gradle/init.d/gradlebench-maven-local.gradle << 'GRADLEBENCH_MAVEN_LOCAL_EOF'
allprojects {
    repositories {
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
    "git clone --filter=blob:none https://github.com/nextcloud/android-common.git /tmp/gradlebench-android-common",
    "cd /tmp/gradlebench-android-common",
    f"git checkout {_ANDROID_COMMON_FULL_COMMIT}",
    "sed -i \"s/group = 'com.nextcloud.android-common'/group = 'com.github.nextcloud.android-common'/\" build.gradle",
    "chmod +x gradlew",
    f"./gradlew --no-daemon -Pversion={_ANDROID_COMMON_COMMIT} publishToMavenLocal",
    "cd /testbed",
    "rm -rf /tmp/gradlebench-android-common",
    _ENABLE_PROJECT_MAVEN_LOCAL,
]

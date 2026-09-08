"""Build the deleted JitPack cert4android dependency from source."""

REPO = "tasks/tasks"

_CERT4ANDROID_COMMIT = "7814052"
_CERT4ANDROID_FULL_COMMIT = "7814052eaf3072ad2c8ed29606cc9f18c3b7921d"

_ENABLE_MAVEN_LOCAL = r"""mkdir -p /root/.gradle/init.d && cat > /root/.gradle/init.d/gradlebench-maven-local.gradle << 'GRADLEBENCH_MAVEN_LOCAL_EOF'
beforeSettings { settings ->
    settings.dependencyResolutionManagement.repositories {
        mavenLocal()
    }
}
GRADLEBENCH_MAVEN_LOCAL_EOF
"""

_ADD_PUBLICATION = rf"""cat >> /tmp/gradlebench-cert4android/build.gradle << 'GRADLEBENCH_CERT4ANDROID_EOF'

apply plugin: 'maven-publish'

afterEvaluate {{
    publishing {{
        publications {{
            release(MavenPublication) {{
                from components.release
                groupId = 'com.github.bitfireAT'
                artifactId = 'cert4android'
                version = '{_CERT4ANDROID_COMMIT}'
            }}
        }}
    }}
}}
GRADLEBENCH_CERT4ANDROID_EOF
"""

COMMANDS = [
    _ENABLE_MAVEN_LOCAL,
    "git clone --filter=blob:none https://github.com/bitfireAT/cert4android.git /tmp/gradlebench-cert4android",
    "cd /tmp/gradlebench-cert4android",
    f"git checkout {_CERT4ANDROID_FULL_COMMIT}",
    _ADD_PUBLICATION,
    "chmod +x gradlew",
    "./gradlew --no-daemon publishReleasePublicationToMavenLocal",
    "cd /testbed",
    "rm -rf /tmp/gradlebench-cert4android",
]

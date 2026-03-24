import platform as _platform


def get_host_arch() -> str:
    """Detect the host CPU architecture.

    Returns:
        "x86_64" on Intel/AMD hosts, "arm64" on Apple Silicon / ARM hosts.
    """
    machine = _platform.machine().lower()
    if machine in ("x86_64", "amd64"):
        return "x86_64"
    elif machine in ("arm64", "aarch64"):
        return "arm64"
    else:
        raise ValueError(
            f"Unsupported host architecture: {machine}. "
            "Expected x86_64/amd64 or arm64/aarch64."
        )


_DOCKERFILE_BASE_KOTLIN = """FROM --platform={platform} gradle:9.3.1-jdk{java_version}-jammy

WORKDIR /home/
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && \
  apt-get install -y --no-install-recommends \
  curl \
  git \
  bash \
  ca-certificates \
  unzip \
  zip \
  libncurses5 \
  libvulkan1 \
  libpulse0 \
  libgl1 \
  libxml2 \
  patch \
  openjdk-11-jdk-headless \
  openjdk-17-jdk-headless \
  openjdk-21-jdk-headless && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

# On ARM64 hosts, Android SDK build tools (aapt2, aidl, etc.) are x86-64-only
# Linux ELFs.  Docker Desktop intercepts them via Rosetta/binfmt_misc emulation,
# but fails immediately because the x86-64 dynamic linker is absent from the
# container.  Adding the amd64 foreign architecture and installing libc6:amd64
# provides /lib64/ld-linux-x86-64.so.2, which lets those binaries load and run.
# On ARM64 Ubuntu the default apt sources (ports.ubuntu.com) only serve ARM
# packages, so we must explicitly add archive.ubuntu.com for amd64 packages.
RUN dpkg --add-architecture amd64 && \
  sed -i 's|^deb http://ports\\.ubuntu\\.com|deb [arch=arm64] http://ports.ubuntu.com|g' /etc/apt/sources.list && \
  printf 'deb [arch=amd64] http://archive.ubuntu.com/ubuntu jammy main restricted universe\\ndeb [arch=amd64] http://archive.ubuntu.com/ubuntu jammy-updates main restricted universe\\ndeb [arch=amd64] http://security.ubuntu.com/ubuntu jammy-security main restricted universe\\n' \
    >> /etc/apt/sources.list && \
  apt-get update && \
  apt-get install -y --no-install-recommends \
  libc6:amd64 \
  libstdc++6:amd64 \
  zlib1g:amd64 && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

RUN update-ca-certificates

# Install SDKMAN and latest Gradle version (9.3.1)
# Update these commands as new Gradle versions are released
RUN curl -s "https://get.sdkman.io" | bash
RUN bash -c "source /root/.sdkman/bin/sdkman-init.sh && \
    sdk install gradle 9.3.1 && \
    sdk default gradle 9.3.1"

# Pre-warm Gradle wrapper distributions referenced in the dataset.
# The script is generated from gradle_distribution_url fields in the dataset.
COPY ./gradle_warmup.sh /tmp/gradle_warmup.sh
RUN bash /tmp/gradle_warmup.sh && rm -f /tmp/gradle_warmup.sh

ENV GRADLE_USER_HOME=/root/.gradle

RUN $JAVA_HOME/bin/keytool -importkeystore -noprompt -trustcacerts \
  -srckeystore /etc/ssl/certs/java/cacerts \
  -destkeystore $JAVA_HOME/lib/security/cacerts \
  -srcstorepass changeit -deststorepass changeit || true

ENV ANDROID_SDK_ROOT=/opt/android-sdk \
    ANDROID_HOME=/opt/android-sdk \
    PATH=$PATH:/opt/android-sdk/cmdline-tools/latest/bin:/opt/android-sdk/platform-tools

RUN mkdir -p ${{ANDROID_SDK_ROOT}}/cmdline-tools && \
  curl -o sdk-tools.zip https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip && \
  unzip sdk-tools.zip -d ${{ANDROID_SDK_ROOT}}/cmdline-tools && \
  mv ${{ANDROID_SDK_ROOT}}/cmdline-tools/cmdline-tools ${{ANDROID_SDK_ROOT}}/cmdline-tools/latest && \
  rm sdk-tools.zip

RUN yes | sdkmanager --licenses && \
  sdkmanager "platform-tools" \
  "platforms;android-30" "platforms;android-31" "platforms;android-32" \
  "platforms;android-33" "platforms;android-34" "platforms;android-35" "platforms;android-36" \
  "build-tools;30.0.3" "build-tools;31.0.0" "build-tools;32.0.0" \
  "build-tools;33.0.0" "build-tools;33.0.1" "build-tools;34.0.0" "build-tools;35.0.0" "build-tools;36.0.0"

"""

def make_gradle_warmup_script(distribution_urls: list[str]) -> str:
    """
    Returns the content of a shell script that pre-warms each Gradle distribution by:
      1. Creating a minimal Gradle project in /tmp/gradle-warmup
      2. Using the system Gradle (9.3.1) to generate a wrapper pointing to the URL
      3. Running ./gradlew --no-daemon help (downloads, extracts, primes tooling API)
      4. Deleting cached ZIPs to reclaim image space
    The script is self-contained with a shebang and set -euo pipefail, suitable
    for being COPY'd and RUN'd as a file in _DOCKERFILE_BASE_KOTLIN.
    """
    lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        "",
        "mkdir -p /tmp/gradle-warmup",
        "cd /tmp/gradle-warmup",
        "printf 'rootProject.name = \"warmup\"\\n' > settings.gradle",
        "",
    ]
    for url in sorted(set(distribution_urls)):
        lines += [
            f"gradle --no-daemon wrapper --gradle-distribution-url '{url}'",
            "./gradlew --no-daemon help",
            "",
        ]
    lines += [
        "find /root/.gradle/wrapper/dists -name '*.zip' -delete",
        "cd /",
        "rm -rf /tmp/gradle-warmup",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Dependency pre-fetch via Gradle init scripts.
#
# Instead of maintaining a static list of dependencies, we inject an init
# script into the real project that registers a "resolveAllDependencies" task
# in every (sub)project.  Running it after the repo is cloned populates the
# Gradle cache with the exact artifacts the project needs.
#
# Two variants are provided because the isolated-projects-compatible API
# (gradle.lifecycle.afterProject) only exists in Gradle >= 8.8.
# ---------------------------------------------------------------------------

# For Gradle >= 8.8: uses the IsolatedAction-based lifecycle hook.
_RESOLVE_DEPS_INIT_GRADLE_MODERN = """\
gradle.lifecycle.afterProject {
    tasks.register("resolveAllDependencies") {
        doLast {
            configurations.matching { it.isCanBeResolved() }.each { config ->
                try {
                    config.resolve()
                } catch (Exception e) {
                    logger.warn("Could not resolve ${config.name}: ${e.message}")
                }
            }
        }
    }
}
"""

# For Gradle < 8.8: uses allprojects + afterEvaluate (not isolated-projects safe).
_RESOLVE_DEPS_INIT_GRADLE_LEGACY = """\
allprojects {
    afterEvaluate {
        tasks.register("resolveAllDependencies") {
            doLast {
                configurations.findAll { it.canBeResolved }.each { config ->
                    try {
                        config.resolve()
                    } catch (Exception e) {
                        println("WARN: could not resolve ${config.name}: ${e.message}")
                    }
                }
            }
        }
    }
}
"""

_GRADLE_8_8 = (8, 8)


def _parse_gradle_version(distribution_url: str) -> tuple[int, ...]:
    """Extract the Gradle version tuple from a distribution URL.

    >>> _parse_gradle_version("https://.../gradle-8.11.1-bin.zip")
    (8, 11, 1)
    """
    import re
    m = re.search(r"gradle-(\d+(?:\.\d+)*)-", distribution_url)
    if not m:
        return (0,)
    return tuple(int(x) for x in m.group(1).split("."))


def get_resolve_deps_init_script(distribution_url: str) -> str:
    """Return the appropriate init script content for the given Gradle version."""
    version = _parse_gradle_version(distribution_url)
    if version >= _GRADLE_8_8:
        return _RESOLVE_DEPS_INIT_GRADLE_MODERN
    return _RESOLVE_DEPS_INIT_GRADLE_LEGACY


_DOCKERFILE_INSTANCE_KOTLIN = r"""FROM --platform={platform} {env_image_name}

COPY ./setup_repo.sh /root/
RUN /bin/bash /root/setup_repo.sh

WORKDIR /testbed/
"""
# Compute shell commands (checkout + gradlew tasks) for each repo in
# gradle_prs_swe_bench_trimmed.json. This is computed at Python/template
# generation time so the instance image does not need Python installed.
import os
import json
import shlex
import platform as _platform_mod

_json_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "gradle_prs_swe_bench_trimmed.json"))
PRIMING_COMMANDS = ""
try:
    with open(_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Expecting a list of objects with 'repo' and optional 'base_commit'
    cmds = []
    if isinstance(data, dict):
        # try to find list under common keys
        for k in ("items", "repos", "data"):
            if k in data and isinstance(data[k], list):
                data = data[k]
                break
    if not isinstance(data, list):
        raise ValueError("unexpected JSON shape; expected list of repo objects")
    for entry in data:
        repo = entry.get("repo") if isinstance(entry, dict) else None
        if not repo:
            continue
        commit = entry.get("base_commit") if isinstance(entry, dict) else None
        repo_dir = repo.replace("/", "__")
        fetch_ref = commit if commit else "HEAD"
        # Build robust shell commands; don't fail Python construction if values odd
        cmds.append(f"echo '=== Priming {repo} {fetch_ref}'; mkdir -p /priming/{repo_dir}")
        cmds.append(f"git init /priming/{repo_dir} >/dev/null 2>&1 || true")
        cmds.append(f"git -C /priming/{repo_dir} remote add origin https://github.com/{repo}.git || true")
        cmds.append(f"git -C /priming/{repo_dir} fetch --depth=1 origin {shlex.quote(fetch_ref)}")
        cmds.append(f"git -C /priming/{repo_dir} checkout -q FETCH_HEAD")
        cmds.append(f"if [ -f \"/priming/{repo_dir}/gradlew\" ]; then chmod +x \"/priming/{repo_dir}/gradlew\"; fi")
        cmds.append(f"cd /priming/{repo_dir} && ./gradlew tasks --no-daemon")
        cmds.append("")
    PRIMING_COMMANDS = "\n".join(cmds)
except Exception as e:
    PRIMING_COMMANDS = f"# Could not compute priming commands: {str(e)}\n"

# Build a heredoc RUN block to embed the priming commands into the Dockerfile
_priming_block = None
if PRIMING_COMMANDS and not PRIMING_COMMANDS.startswith('# Could not compute'):
    # Ensure the commands end with a newline
    priming_body = PRIMING_COMMANDS.rstrip() + "\n"
    # Use a quoted heredoc so the commands are not interpolated by the shell
    _priming_block = (
        "RUN bash -euo pipefail <<'PRIMING_SCRIPT'\n"
        + priming_body
        + "PRIMING_SCRIPT\n\n"
    )
else:
    # If we couldn't compute commands, emit a harmless comment in the Dockerfile
    _priming_block = "# Priming commands not available at template-generation time\n\n"

# Detect host/platform and map to a sensible Docker platform string.
# Allow an environment override via DOCKER_DEFAULT_PLATFORM if callers want to force a platform.
_DEFAULT_PLATFORM = None
_env_override = os.environ.get("DOCKER_DEFAULT_PLATFORM") or os.environ.get("SWE_BENCH_DOCKER_PLATFORM")
if _env_override:
    _DEFAULT_PLATFORM = _env_override
else:
    try:
        _arch = _platform_mod.machine() or ""
        _arch = _arch.lower()
        if _arch in ("x86_64", "amd64", "i386", "i686"):
            _DEFAULT_PLATFORM = "linux/amd64"
        elif _arch in ("arm64", "aarch64"):
            _DEFAULT_PLATFORM = "linux/arm64"
        elif _arch.startswith("armv7") or _arch.startswith("armv6"):
            _DEFAULT_PLATFORM = "linux/arm/v7"
        else:
            # conservative default
            _DEFAULT_PLATFORM = "linux/amd64"
    except Exception:
        _DEFAULT_PLATFORM = "linux/amd64"

# Provide an explanatory variable for consumers of this module
DETECTED_DOCKER_PLATFORM = _DEFAULT_PLATFORM

_DOCKERFILE_BASE_KOTLIN = """FROM --platform={platform} gradle:8.13-jdk{java_version}-jammy

WORKDIR /home/
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# Enable multiarch for x86_64 compatibility (needed for Android SDK tools on ARM64)
RUN dpkg --add-architecture amd64 || true

# Configure apt sources for multiarch support on ARM64
# ARM64 packages from ports.ubuntu.com, amd64 packages from archive.ubuntu.com
RUN if [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "arm64" ]; then \
  cp /etc/apt/sources.list /etc/apt/sources.list.bak && \
  echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy main restricted universe multiverse" > /etc/apt/sources.list && \
  echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
  echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
  echo "deb [arch=arm64] http://ports.ubuntu.com/ubuntu-ports jammy-security main restricted universe multiverse" >> /etc/apt/sources.list && \
  echo "deb [arch=amd64] http://archive.ubuntu.com/ubuntu jammy main restricted universe multiverse" >> /etc/apt/sources.list && \
  echo "deb [arch=amd64] http://archive.ubuntu.com/ubuntu jammy-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
  echo "deb [arch=amd64] http://archive.ubuntu.com/ubuntu jammy-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
  echo "deb [arch=amd64] http://security.ubuntu.com/ubuntu jammy-security main restricted universe multiverse" >> /etc/apt/sources.list; \
fi

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

# Install x86_64 libraries needed for Rosetta translation of Android SDK tools
# This allows x86_64 binaries like AAPT2 to run on ARM64 via Rosetta
RUN if [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "arm64" ]; then \
  apt-get update && \
  apt-get install -y --no-install-recommends \
    libc6:amd64 \
    libstdc++6:amd64 \
    zlib1g:amd64 && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*; \
fi

RUN update-ca-certificates

# Install SDKMAN and Gradle 9.3.1 (used to bootstrap wrapper installations)
RUN curl -s "https://get.sdkman.io" | bash
RUN bash -c "source /root/.sdkman/bin/sdkman-init.sh && \
    sdk install gradle 9.3.1 && \
    sdk default gradle 9.3.1"

# Create a Gradle build directory with settings.gradle to use wrapper for installing other versions
RUN mkdir -p /priming/gradle && \
  echo "" > /priming/gradle/settings.gradle

# Install various Gradle versions using the Gradle wrapper
# This ensures all versions are pre-installed and ready for use
RUN bash -c "cd /priming/gradle && \
    gradle wrapper --gradle-version=7.6.1 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.0 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.6 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.8 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.9 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.10.2 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.11.1 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.12.1 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.13 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.14.3 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=8.14.4 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=9.0.0 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=9.1.0 && ./gradlew help --no-daemon && \
    gradle wrapper --gradle-version=9.2.1 && ./gradlew help --no-daemon"

RUN mkdir -p /root/.gradle && \
  echo "org.gradle.jvmargs=-Xmx8g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.java.installations.auto-detect=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.java.installations.auto-download=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.caching=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.parallel=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.vfs.watch=false" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.workers.max=24" >> /root/.gradle/gradle.properties

ENV JAVA_OPTS="-Xmx8g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8"
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
  "platforms;android-33" "platforms;android-34" "platforms;android-35" \
  "build-tools;30.0.3" "build-tools;31.0.0" "build-tools;32.0.0" \
  "build-tools;33.0.0" "build-tools;34.0.0" "build-tools;35.0.0"

""" + _priming_block

# Replace the {platform} placeholder with the detected default platform to avoid
# requesting an image platform that doesn't match the host (which causes the
# Docker warning). If callers explicitly format the template with a platform
# later, they can override this behavior by providing their own platform.
_DOCKERFILE_BASE_KOTLIN = _DOCKERFILE_BASE_KOTLIN.replace("{platform}", DETECTED_DOCKER_PLATFORM)

_DOCKERFILE_INSTANCE_KOTLIN = r"""FROM --platform={platform} {env_image_name}

COPY ./setup_repo.sh /root/
RUN /bin/bash /root/setup_repo.sh

WORKDIR /testbed/
"""

# Also replace the {platform} in the instance template with the detected default.
# This makes the templates generated on e.g. Apple Silicon request linux/arm64 by default.
_DOCKERFILE_INSTANCE_KOTLIN = _DOCKERFILE_INSTANCE_KOTLIN.replace("{platform}", DETECTED_DOCKER_PLATFORM)

_DOCKERFILE_BASE_KOTLIN = """FROM --platform={platform} gradle:8.13-jdk{java_version}-jammy

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
  openjdk-11-jdk-headless \
  openjdk-17-jdk-headless \
  openjdk-21-jdk-headless && \
  apt-get clean && \
  rm -rf /var/lib/apt/lists/*

RUN update-ca-certificates

# Install SDKMAN and various Gradle versions used by test data
# Add to this list as new Gradle versions are discovered in use by test data)
RUN curl -s "https://get.sdkman.io" | bash
RUN bash -c "source /root/.sdkman/bin/sdkman-init.sh && \
    sdk install gradle 8.6 && \
    sdk install gradle 8.8 && \
    sdk install gradle 8.9 && \
    sdk install gradle 8.10.2 && \
    sdk install gradle 8.11.1 && \
    sdk install gradle 8.12.1 && \
    sdk install gradle 8.13 && \
    sdk install gradle 8.14.3 && \
    sdk install gradle 8.14.4 && \
    sdk install gradle 9.0.0 && \
    sdk install gradle 9.1.0 && \
    sdk install gradle 9.2.1 && \
    sdk install gradle 9.3.1 && \
    sdk default gradle 9.3.1"

RUN mkdir -p /root/.gradle && \
  echo "org.gradle.jvmargs=-Xmx20g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.java.installations.auto-detect=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.java.installations.auto-download=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.caching=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.parallel=true" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.vfs.watch=false" >> /root/.gradle/gradle.properties && \
  echo "org.gradle.workers.max=24" >> /root/.gradle/gradle.properties

ENV GRADLE_OPTS="-Xmx20g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8"
ENV JAVA_OPTS="-Xmx20g -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8"
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
"""

_DOCKERFILE_INSTANCE_KOTLIN = r"""FROM --platform={platform} {env_image_name}

COPY ./setup_repo.sh /root/
RUN /bin/bash /root/setup_repo.sh

WORKDIR /testbed/
"""
#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: GATEWAY_IP=<address> [CA_CERT=<path>] $0" >&2
  exit 2
}

[[ -n ${GATEWAY_IP:-} ]] || usage

curl_args=(--fail --silent --show-error --output /dev/null)
if [[ -n ${CA_CERT:-} ]]; then curl_args+=(--cacert "$CA_CERT"); fi

check() {
  local host="$1" path="$2"
  curl "${curl_args[@]}" --resolve "$host:443:$GATEWAY_IP" "https://$host$path"
  echo "ok: $host$path"
}

check repo.maven.apache.org /maven2/org/jetbrains/kotlin/kotlin-stdlib/1.9.0/kotlin-stdlib-1.9.0.pom
check repo1.maven.org /maven2/org/jetbrains/kotlin/kotlin-stdlib/1.9.0/kotlin-stdlib-1.9.0.pom
check plugins.gradle.org /m2/org/jetbrains/kotlin/jvm/org.jetbrains.kotlin.jvm.gradle.plugin/1.9.0/org.jetbrains.kotlin.jvm.gradle.plugin-1.9.0.pom
check maven.reposilite.com /maven-central/org/jetbrains/kotlin/kotlin-stdlib/1.9.0/kotlin-stdlib-1.9.0.pom
check maven.reposilite.com /releases/com/reposilite/reposilite/3.5.19/reposilite-3.5.19.pom

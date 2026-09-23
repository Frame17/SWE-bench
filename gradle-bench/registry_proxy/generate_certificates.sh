#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${DEPENDENCY_GATEWAY_STATE_DIR:-$HERE/.state}"

command -v openssl >/dev/null 2>&1 || {
  echo "ERROR: openssl is required to generate dependency gateway certificates" >&2
  exit 1
}

mkdir -p "$STATE_DIR"
work_dir="$(mktemp -d "$STATE_DIR/.generate.XXXXXX")"
cleanup() {
  if [[ $work_dir == "$STATE_DIR"/.generate.* ]]; then
    rm -rf "$work_dir"
  fi
}
trap cleanup EXIT INT TERM

ca_cert="$STATE_DIR/ca.crt"
ca_key="$STATE_DIR/ca.key"
new_ca=0

if [[ -f $ca_cert || -f $ca_key ]]; then
  if [[ ! -f $ca_cert || ! -f $ca_key ]]; then
    echo "ERROR: dependency gateway CA state is incomplete in $STATE_DIR" >&2
    exit 1
  fi
else
  openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 3650 \
    -subj '/CN=Kotlin dependency gateway CA' \
    -addext 'basicConstraints=critical,CA:TRUE' \
    -addext 'keyUsage=critical,keyCertSign,cRLSign' \
    -keyout "$work_dir/ca.key" -out "$work_dir/ca.crt" >/dev/null 2>&1
  ca_cert="$work_dir/ca.crt"
  ca_key="$work_dir/ca.key"
  new_ca=1
fi

leaf_is_current() {
  [[ -f $STATE_DIR/tls.crt && -f $STATE_DIR/tls.key ]] || return 1
  openssl x509 -in "$STATE_DIR/tls.crt" -noout -checkend 86400 >/dev/null 2>&1 || return 1
  openssl verify -CAfile "$ca_cert" "$STATE_DIR/tls.crt" >/dev/null 2>&1 || return 1
  cmp -s \
    <(openssl x509 -in "$STATE_DIR/tls.crt" -pubkey -noout 2>/dev/null) \
    <(openssl pkey -in "$STATE_DIR/tls.key" -pubout 2>/dev/null) || return 1

  local host
  while read -r host; do
    [[ -n $host ]] || continue
    openssl x509 -in "$STATE_DIR/tls.crt" -noout -checkhost "$host" 2>/dev/null |
      grep -Fq "Hostname $host does match certificate" || return 1
  done < <(sed -n 's/^subjectAltName=//p' "$HERE/tls.ext" | tr ',' '\n' | sed 's/^DNS://')
}

if ((new_ca == 0)) && leaf_is_current; then
  exit 0
fi

openssl req -newkey rsa:2048 -nodes -sha256 \
  -subj '/CN=repo.maven.apache.org' \
  -keyout "$work_dir/tls.key" -out "$work_dir/tls.csr" >/dev/null 2>&1
openssl x509 -req -sha256 -days 3650 \
  -in "$work_dir/tls.csr" -CA "$ca_cert" -CAkey "$ca_key" \
  -CAcreateserial -extfile "$HERE/tls.ext" -out "$work_dir/tls.crt" >/dev/null 2>&1

chmod 600 "$work_dir/tls.key"
if ((new_ca)); then
  chmod 600 "$work_dir/ca.key"
  mv "$work_dir/ca.crt" "$work_dir/ca.key" "$STATE_DIR/"
fi
mv "$work_dir/tls.crt" "$work_dir/tls.key" "$STATE_DIR/"

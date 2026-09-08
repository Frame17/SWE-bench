# Transparent dependency registry gateway

The gateway preserves the repository URLs used by Gradle while routing Maven Central through
Google's hosted mirror. The Gradle Plugin Portal passes through by default. Maven Central paths
on Reposilite use the mirror, while other Reposilite paths pass through to the original server.

`../build_dataset.sh` starts the gateway automatically when `DEPENDENCY_GATEWAY` is unset. It
generates a local CA under `.state/`, starts the Compose service on port 443, adds the original
repository hostnames to Docker builds, and installs the CA in Kotlin system and Java trust
stores. The service remains running after the build.

Set `DEPENDENCY_GATEWAY` to an existing gateway address to skip local startup. Set it to an empty
value to disable routing. A custom `DEPENDENCY_GATEWAY_ENV_FILE` requires
`DEPENDENCY_GATEWAY_CA_CERT`. The Compose environment also accepts custom TLS files, upstream CA,
upstream authorization headers, and Maven or Plugin Portal upstream addresses.

Verify a running gateway with:

```bash
GATEWAY_IP=127.0.0.1 CA_CERT=.state/ca.crt ./verify_gateway.sh
```

Stop the local service with:

```bash
docker compose down
```

The CA private key permits interception of the configured repository hostnames. Keep `.state/`
private.

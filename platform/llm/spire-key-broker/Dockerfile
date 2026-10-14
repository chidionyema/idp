# SPIRE Key Broker image.
# - OCI CLI: calls OCI Vault via workload identity (no static key)
# - spire-agent: verifies the caller's SVID before returning a key
# - Go broker: HTTP server + vault fetch
#
# 2026-10-14: this image had never built. Its base, ghcr.io/oracle/oraclelinux9-oci-cli, is
# gone (404); the SPIRE asset `linux-x86_64` does not exist (releases ship
# `linux-<arch>-musl`), which also baked an x86 binary into the arm64 image; and
# `COPY spire-key-broker` copied a binary nothing built. Nobody saw it because
# build-multiarch builds only the images a change reaches, and nothing had touched this
# one since #3947. The layout is cmd/identity-bootstrapper's, which builds the same
# OCI CLI + spire-agent pair.

# Build the broker. Stdlib only.
FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.26.3-alpine AS builder
ARG TARGETARCH
WORKDIR /builder
COPY go.mod ./
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags='-w -s' -o /builder/spire-key-broker .

# Download the SPIRE agent binary. Used by the broker's verifySVID function to
# verify callers' SVIDs via the Workload API socket. The agent runs in the pod as
# a DaemonSet (spire-agent, separate from this binary); we only need the CLI.
FROM docker.io/library/alpine:3.21 AS spire
ARG TARGETARCH
ARG SPIRE_VERSION=1.15.3
RUN apk add --no-cache curl && \
    curl -fsSL "https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-${TARGETARCH}-musl.tar.gz" -o /tmp/spire.tar.gz && \
    tar xzf /tmp/spire.tar.gz -C /tmp && \
    mv /tmp/spire-${SPIRE_VERSION}/bin/spire-agent /usr/local/bin/spire-agent && \
    chmod 755 /usr/local/bin/spire-agent

# OCI CLI on Oracle Linux 9, pinned. jq for JSON parsing.
FROM ghcr.io/oracle/oraclelinux:9
ARG OCI_CLI_VERSION=3.94.1
RUN dnf install -y --nodocs python3.12 python3.12-pip jq && \
    python3.12 -m pip install --no-cache-dir "oci-cli==${OCI_CLI_VERSION}" && \
    dnf clean all && rm -rf /var/cache/dnf
COPY --from=spire /usr/local/bin/spire-agent /usr/local/bin/spire-agent
COPY --from=builder --chown=10001:10001 /builder/spire-key-broker /usr/local/bin/spire-key-broker
# Run as non-root, matching the router's security posture.
USER 10001
ENTRYPOINT ["/usr/local/bin/spire-key-broker"]

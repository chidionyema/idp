# cmd/identity-bootstrapper/Dockerfile
# Layer 1: Cryptographic Bootstrapper Init Container.
# Oracle Linux 9 base with OCI CLI and the SPIRE agent binary (the bootstrapper shells out to
# `spire-agent api fetch jwt` and `oci`).
#
# Until 2026-09-30 this file did not build: the spire download URL (spire-<v>-linux-x86_64.tar.gz)
# answers 404 (measured), the first stage was never named so `COPY --from=builder` read the golang
# stage that has no spire-agent, and amd64 was hard-coded. Now: one stage fetches the SPIRE musl
# release for $TARGETARCH (a static Go binary, it runs on glibc), one cross-compiles the
# bootstrapper, and the runtime stage joins them.
FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.23.5-alpine3.21 AS builder
ARG TARGETARCH
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY go.mod ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags='-w -s' -o /builder/bootstrapper main.go

FROM docker.io/library/alpine:3.21 AS spire
ARG TARGETARCH
ARG SPIRE_VERSION=1.15.3
RUN apk add --no-cache curl && \
    curl -fsSL "https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-${TARGETARCH}-musl.tar.gz" -o /tmp/spire.tar.gz && \
    tar xzf /tmp/spire.tar.gz -C /tmp && \
    mv /tmp/spire-${SPIRE_VERSION}/bin/spire-agent /usr/local/bin/spire-agent && \
    chmod 755 /usr/local/bin/spire-agent

FROM ghcr.io/oracle/oraclelinux:9
# The OCI CLI is not packaged in any Oracle Linux 9 repo the image carries (measured 2026-09-30:
# `oci` and `*oci-cli*` absent from ol9_baseos/appstream/developer, oracle-epel-ol9 unavailable),
# so it comes from PyPI, pinned. Only the OCI key path shells out to it; EPHEMERAL_KEY mode does not.
ARG OCI_CLI_VERSION=3.94.1
RUN dnf install -y --nodocs python3.12 python3.12-pip jq && \
    python3.12 -m pip install --no-cache-dir "oci-cli==${OCI_CLI_VERSION}" && \
    dnf clean all && rm -rf /var/cache/dnf
COPY --from=spire /usr/local/bin/spire-agent /usr/local/bin/spire-agent
COPY --from=builder /builder/bootstrapper /bootstrapper
USER 10001:10001
ENTRYPOINT ["/bootstrapper"]

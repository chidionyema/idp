# cmd/identity-bootstrapper/Dockerfile
# Layer 1: Cryptographic Bootstrapper Init Container.
# Ubuntu base with OCI CLI (workload identity auth) and SPIRE agent (JWT-SVID).
# No OCI Go SDK dependency — uses OCI CLI + Go standard library.

FROM docker.io/library/ubuntu:24.04 AS base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl jq ca-certificates && \
        apt-get clean && rm -rf /var/lib/apt/lists/*

# Install SPIRE agent binary.
ENV SPIRE_VERSION=1.15.3
RUN curl -fsSL \
        "https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-x86_64.tar.gz" \
        -o /tmp/spire.tar.gz \
    && tar xzf /tmp/spire.tar.gz -C /tmp \
    && mv /tmp/spire-${SPIRE_VERSION}/bin/spire-agent /usr/local/bin/ \
    && chmod 755 /usr/local/bin/spire-agent \
    && rm -rf /tmp/spire*

# Install OCI CLI (for Vault access via workload identity).
RUN curl -fsSL https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh \
        | OCI_CLI_VERSION="3.40.0" OCI_CLI_SKIP_DOWNLOAD=true bash -s run \
    || echo "OCI CLI install note: update OCI_CLI_VERSION if needed"

# Build Go binary.
FROM docker.io/library/golang:1.23-alpine AS builder
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY cmd/identity-bootstrapper/go.mod ./
RUN go mod download
COPY cmd/identity-bootstrapper/*.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/bootstrapper main.go

# Final image.
FROM docker.io/library/ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl jq ca-certificates && \
        apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=base /usr/local/bin/spire-agent /usr/local/bin/spire-agent
COPY --from=base /usr/bin/oci /usr/bin/oci
COPY --from=base /usr/bin/curl /usr/bin/curl
COPY --from=builder /builder/bootstrapper /bootstrapper
ENTRYPOINT ["/bootstrapper"]

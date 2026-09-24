# Stage 1: compile the Go broker binary.
FROM docker.io/library/golang:1.23-alpine AS builder
WORKDIR /src
RUN apk add --no-cache ca-certificates
COPY server.go .
# CGO_ENABLED=0 → static binary, no libc dep → runs on both amd64 and arm64.
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o spire-key-broker server.go

# Stage 2: thin runtime image.
# Oracle install script fetches the correct architecture binary at build time.
# SPIRE releases publish separate tarballs for x86_64 and aarch64.
FROM docker.io/library/debian:12-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv curl jq ca-certificates \
    && curl -fsSL https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh \
        | BINARY_VERSION="3.41.0" bash -s -- --accept-all-defaults \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

ENV SPIRE_VERSION=1.15.3
# SPIRE publishes separate tarballs per arch; uname -m resolves to the correct URL.
RUN ARCH="$(uname -m)" \
    && [ "$ARCH" = "x86_64" ] && SPIRE_ARCH="x86_64" \
    || SPIRE_ARCH="aarch64" \
    && curl -fsSL \
        "https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-${SPIRE_ARCH}.tar.gz" \
        -o /tmp/spire.tar.gz \
    && tar xzf /tmp/spire.tar.gz -C /tmp \
    && mv /tmp/spire-${SPIRE_VERSION}/bin/spire-agent /usr/local/bin/ \
    && chmod 755 /usr/local/bin/spire-agent \
    && rm -rf /tmp/spire*

COPY --from=builder /src/spire-key-broker /usr/local/bin/spire-key-broker

USER 10001
ENTRYPOINT ["/usr/local/bin/spire-key-broker"]

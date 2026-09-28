# cmd/identity-bootstrapper/Dockerfile
# Layer 1: Cryptographic Bootstrapper Init Container
# Based on Oracle Linux 9 + OCI CLI (like spire-key-broker pattern).
# No Go SDK dependency; uses OCI CLI for Vault access.
FROM ghcr.io/oracle/oraclelinux9-oci-cli:latest AS oci-cli

# Install SPIRE agent binary (for JWT-SVID fetch via Workload API socket).
ENV SPIRE_VERSION=1.15.3
RUN curl -fsSL \
        "https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-x86_64.tar.gz" \
        -o /tmp/spire.tar.gz \
    && tar xzf /tmp/spire.tar.gz -C /tmp \
    && mv /tmp/spire-${SPIRE_VERSION}/bin/spire-agent /usr/local/bin/ \
    && chmod 755 /usr/local/bin/spire-agent \
    && rm -rf /tmp/spire*

# Build the Go binary.
FROM docker.io/library/golang:1.23-alpine AS builder-go
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY cmd/identity-bootstrapper/go.mod ./
RUN go mod download
COPY cmd/identity-bootstrapper/*.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/bootstrapper main.go

# Final image: combine OCI CLI + Go binary in a minimal image.
FROM ghcr.io/oracle/oraclelinux9-oci-cli:latest
# Copy SPIRE agent from the oci-cli stage.
COPY --from=oci-cli /usr/local/bin/spire-agent /usr/local/bin/spire-agent
# Copy the compiled Go binary from the builder stage.
COPY --from=builder-go /builder/bootstrapper /bootstrapper
ENTRYPOINT ["/bootstrapper"]

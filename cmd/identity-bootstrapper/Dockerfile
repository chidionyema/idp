# cmd/identity-bootstrapper/Dockerfile
# Layer 1: Cryptographic Bootstrapper Init Container.
# Oracle Linux 9 base with OCI CLI and SPIRE agent.
FROM ghcr.io/oracle/oraclelinux9:9

# Install OCI CLI and dependencies.
RUN dnf install -y --nodocs oracle-epel-ol9 && \
    dnf install -y --nodocs oci jq && \
    dnf clean all

# Install SPIRE agent binary.
ENV SPIRE_VERSION=1.15.3
RUN curl -fsSL \
        "https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-x86_64.tar.gz" \
        -o /tmp/spire.tar.gz && \
    tar xzf /tmp/spire.tar.gz -C /tmp && \
    mv /tmp/spire-${SPIRE_VERSION}/bin/spire-agent /usr/local/bin/ && \
    chmod 755 /usr/local/bin/spire-agent && \
    rm -rf /tmp/spire*

# Build Go binary.
FROM docker.io/library/golang:1.23.5-alpine3.21 AS builder
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY go.mod ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/bootstrapper main.go

# Final image.
FROM ghcr.io/oracle/oraclelinux9:9
RUN dnf install -y --nodocs oracle-epel-ol9 && \
    dnf install -y --nodocs oci jq && \
    dnf clean all
COPY --from=builder /usr/local/bin/spire-agent /usr/local/bin/spire-agent
COPY --from=builder /builder/bootstrapper /bootstrapper
ENTRYPOINT ["/bootstrapper"]

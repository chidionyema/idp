# cmd/elpis-proxy/Dockerfile
# Layer 3: Elpis Cryptographic Signing Sidecar Proxy.
# R24: built for amd64 and arm64 by build-multiarch.yml on native runners. The binary is
# cross-compiled to $TARGETARCH, never a hard-coded amd64: until 2026-09-30 GOARCH=amd64 was
# fixed here, so the arm64 image (the OKE nodes are arm64) held an x86 binary that cannot exec.
FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.23.5-alpine3.21 AS builder
ARG TARGETARCH
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY go.mod ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags='-w -s' -o /builder/elpis-proxy main.go

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /builder/elpis-proxy /elpis-proxy
EXPOSE 8080
ENTRYPOINT ["/elpis-proxy"]

# cmd/elpis-proxy/Dockerfile
# Layer 3: Elpis Cryptographic Signing Sidecar Proxy.
# Static Go binary on distroless base.
FROM docker.io/library/golang:1.23-alpine AS builder
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY cmd/elpis-proxy/go.mod ./
RUN go mod download
COPY cmd/elpis-proxy/*.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/elpis-proxy main.go

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /builder/elpis-proxy /elpis-proxy
EXPOSE 8080
ENTRYPOINT ["/elpis-proxy"]

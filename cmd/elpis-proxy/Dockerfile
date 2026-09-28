# cmd/elpis-proxy/Dockerfile
# Layer 3: Elpis Cryptographic Signing Sidecar Proxy.
FROM docker.io/library/golang:1.23.5-alpine3.21 AS builder
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY go.mod ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/elpis-proxy main.go

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /builder/elpis-proxy /elpis-proxy
EXPOSE 8080
ENTRYPOINT ["/elpis-proxy"]

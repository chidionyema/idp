# cmd/quad-ledger/Dockerfile
# Layer 4: tamper-evident history (consume, anchor, verify) for the Quad.
# R24: built for amd64 and arm64 by build-multiarch.yml (bin/dockerfiles discovers this file).
FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.23.5-alpine3.21 AS builder
ARG TARGETARCH
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags='-w -s' -o /builder/quad-ledger .

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /builder/quad-ledger /quad-ledger
ENTRYPOINT ["/quad-ledger"]

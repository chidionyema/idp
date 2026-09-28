# cmd/dros-daemon/Dockerfile
# Layer 4: DROS eBPF Enforcement Engine (user-space daemon).
FROM docker.io/library/golang:1.23.5-alpine3.21 AS builder
RUN apk add --no-cache ca-certificates gcc musl-dev clang llvm libbpf-dev
WORKDIR /builder
COPY go.mod ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/dros-daemon main.go

FROM docker.io/library/ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
        clang llvm libbpf-dev && \
        apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=builder /builder/dros-daemon /dros-daemon
COPY bpf/dros_enforce.bpf.c /opt/dros/dros_enforce.bpf.c
COPY bpf/Makefile /opt/dros/Makefile
ENTRYPOINT ["/dros-daemon"]

# cmd/dros-daemon/Dockerfile
# Layer 4: DROS eBPF Enforcement Engine (user-space daemon).
# Privileged container with CAP_BPF + CAP_SYS_ADMIN.
# Ubuntu for clang/llvm (BPF compilation). Multi-stage for small image.
FROM docker.io/library/ubuntu:24.04 AS builder-clang
RUN apt-get update && apt-get install -y --no-install-recommends \
        clang llvm libbpf-dev linux-headers-generic && \
        apt-get clean && rm -rf /var/lib/apt/lists/*

FROM docker.io/library/golang:1.23-alpine AS builder-go
RUN apk add --no-cache ca-certificates gcc musl-dev linux-headers
WORKDIR /builder
COPY cmd/dros-daemon/go.mod ./
RUN go mod download
COPY cmd/dros-daemon/*.go ./
RUN CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/dros-daemon main.go

FROM docker.io/library/ubuntu:24.04
# Ubuntu has BPF toolchain; install for BPF compilation at deploy time.
RUN apt-get update && apt-get install -y --no-install-recommends \
        clang llvm libbpf-dev linux-headers-generic && \
        apt-get clean && rm -rf /var/lib/apt/lists/*
COPY --from=builder-go /builder/dros-daemon /dros-daemon
COPY bpf/dros_enforce.bpf.c /opt/dros/dros_enforce.bpf.c
COPY bpf/Makefile /opt/dros/Makefile
# Pre-compile BPF bytecode (requires kernel headers at build time; graceful fail otherwise).
RUN clang -g -O2 -target bpf -D__TARGET_ARCH_x86 \
        -I/usr/include/x86_64-linux-gnu \
        -c /opt/dros/dros_enforce.bpf.c -o /opt/dros/dros_enforce.bpf.o 2>&1 || \
    echo "NOTE: BPF compilation requires matching kernel headers; compile at deploy time"
ENTRYPOINT ["/dros-daemon"]

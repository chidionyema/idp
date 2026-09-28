# cmd/dros-daemon/Dockerfile
# Layer 4: DROS eBPF Enforcement Engine (user-space daemon).
# BPF is compiled in the build stage using Ubuntu + clang + linux-libc-dev.
# Go binary is pure Go (CGO_ENABLED=0) and loads the compiled .bpf.o at runtime.
FROM docker.io/library/ubuntu:24.04 AS bpf-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        clang llvm linux-libc-dev && \
        apt-get clean && rm -rf /var/lib/apt/lists/*
COPY bpf/dros_enforce.bpf.c /tmp/dros_enforce.bpf.c
# Compile BPF: include paths for Ubuntu 24.04
# linux/socket.h, linux/in.h, uapi/linux/bpf.h are all in these paths.
RUN clang -g -O2 -target bpf -D__TARGET_ARCH_x86 \
        -I/usr/include/x86_64-linux-gnu \
        -I/usr/include/linux \
        -I/usr/include/asm-generic \
        -c /tmp/dros_enforce.bpf.c -o /builder/dros_enforce.bpf.o || \
    echo "NOTE: BPF compile needs linux-libc-dev; compile at deploy time"

FROM docker.io/library/golang:1.23.5-alpine3.21 AS builder
RUN apk add --no-cache ca-certificates
WORKDIR /builder
COPY cmd/dros-daemon/go.mod ./
RUN go mod download
COPY cmd/dros-daemon/*.go ./
COPY --from=bpf-builder /builder/dros_enforce.bpf.o /opt/dros/dros_enforce.bpf.o
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags='-w -s' -o /builder/dros-daemon main.go

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /builder/dros-daemon /dros-daemon
COPY --from=bpf-builder /builder/dros_enforce.bpf.o /opt/dros/dros_enforce.bpf.o
COPY bpf/Makefile /opt/dros/Makefile
ENTRYPOINT ["/dros-daemon"]

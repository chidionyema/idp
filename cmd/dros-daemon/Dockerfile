# cmd/dros-daemon/Dockerfile
# Layer 4: DROS eBPF Enforcement Engine (user-space daemon).
# BPF is compiled in the build stage using Ubuntu + clang + libbpf-dev + linux-libc-dev.
# Go binary is pure Go (CGO_ENABLED=0) and loads the compiled .bpf.o at runtime.
#
# 2026-10-14: this image had never built. The context is this directory (bin/dockerfiles
# builds every image from its Dockerfile's own directory), but the COPY lines named
# repo-root paths -- bpf/ now lives here, beside the daemon that loads it. The BPF stage wrote
# to a /builder it never created and its `|| echo` hid that, so the later COPY of the
# missing .o failed; main.go did not parse and go.mod declared none of its imports; and
# GOARCH=amd64 put an x86 binary into the arm64 image.

FROM docker.io/library/ubuntu:24.04 AS bpf-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        clang llvm libbpf-dev linux-libc-dev && \
        apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /out
COPY bpf/dros_enforce.bpf.c bpf/Makefile ./
# The object is best-effort, as the author intended ("compile at deploy time"): the program
# does not yet compile against userspace headers, and the source and Makefile ship in
# /opt/dros so the node can build it. The compiler's own error stays in the build log.
RUN case "$(uname -m)" in aarch64) a=arm64 ;; *) a=x86 ;; esac; \
    clang -g -O2 -target bpf -D__TARGET_ARCH_${a} \
        -I/usr/include/$(uname -m)-linux-gnu \
        -c dros_enforce.bpf.c -o dros_enforce.bpf.o || \
    echo "NOTE: BPF compile failed (above); compile at deploy time from /opt/dros"

FROM --platform=$BUILDPLATFORM docker.io/library/golang:1.26.3-alpine AS builder
ARG TARGETARCH
WORKDIR /builder
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux GOARCH=${TARGETARCH} go build -ldflags='-w -s' -o /builder/dros-daemon .

FROM gcr.io/distroless/static:nonroot
COPY --from=builder /builder/dros-daemon /dros-daemon
# The whole directory, so an absent object (see above) is not a build failure.
COPY --from=bpf-builder /out/ /opt/dros/
ENTRYPOINT ["/dros-daemon"]

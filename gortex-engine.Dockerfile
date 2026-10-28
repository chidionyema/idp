# The private context engine: Gortex (github.com/zzet/gortex), v0.64.11.
#
# This image is the engine and ONLY the engine. It has no Service, no route and no public
# address: it runs as a sidecar in the broker's pod and binds loopback, so the only way in is
# through the broker's policy. The engine is pinned by the SHA-256 of the release tarball, not
# by a tag: a tag can be moved, a digest cannot.
#
# WHY THE PIN IS IN THE FILE. The checksums published with the release are what a build could
# fetch and trust at build time; a checksum written here is what a build can VERIFY. Both are
# the same value, and the value in this file is the one the release published for v0.64.11.
#
# THE INDEX IS NOT BUILT HERE. The engine's index for a commit is built by CI
# (.github/workflows/context-index.yml) and shipped in the context-index artifact; this image
# carries the binary that serves it. Indexing in the pod would cost minutes of node CPU for
# every restart, and the node's whole request budget is 1.8 CPU.
FROM docker.io/debian:bookworm-slim
# curl is here for two reasons, and both are load-bearing. The build step below fetches the
# release tarball with it -- debian:bookworm-slim ships no curl, so without this the image
# build fails at the fetch. And the pod's probe for this container is an exec probe that
# asks the daemon's own /healthz: the engine binds loopback, so a kubelet httpGet or
# tcpSocket probe (which arrives on the pod's address) can never reach it, and an exec probe
# inside the container can. The engine's liveness is therefore a real question asked of the
# daemon itself, not a file that exists.
RUN apt-get update \
 && apt-get upgrade -y \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --system --uid 10001 --create-home --home-dir /data/home engine
# build-multiarch.yml builds this file for BOTH linux/amd64 and linux/arm64, so the asset is
# derived from the build's own target architecture rather than typed. TARGETARCH is exported by
# buildkit on every build, amd64 and arm64 alike.
ARG TARGETARCH
ARG GORTEX_VERSION=v0.64.11
ARG GORTEX_SHA_AMD64=dc137254d81fa1dca6a3db4239f2d3c045dbbca66b0b07870b4e512d256a2bc7
ARG GORTEX_SHA_ARM64=4a6d0ed502673c86451608ad625b52601054a630af627de911a7c6f9d01eeeb0
RUN set -eux; \
    arch="${TARGETARCH}"; \
    case "${arch}" in \
      amd64) sha="${GORTEX_SHA_AMD64}" ;; \
      arm64) sha="${GORTEX_SHA_ARM64}" ;; \
      *) echo "gortex-engine: no release asset for ${arch}" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/gortex.tar.gz \
      "https://github.com/zzet/gortex/releases/download/${GORTEX_VERSION}/gortex_linux_${arch}.tar.gz"; \
    echo "${sha}  /tmp/gortex.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/gortex && tar xzf /tmp/gortex.tar.gz -C /tmp/gortex; \
    binary="$(find /tmp/gortex -type f -name gortex | head -1)"; \
    test -n "${binary}"; \
    install -m 0755 "${binary}" /usr/local/bin/gortex; \
    rm -rf /tmp/gortex /tmp/gortex.tar.gz; \
    gortex --version
USER engine
ENV HOME=/data/home
EXPOSE 7411
CMD ["gortex", "daemon", "start", "--http-addr", "127.0.0.1:7411"]

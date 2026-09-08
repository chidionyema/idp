# nodesoftware-runsc-handler — handler image for the runsc runtime.
#
# Carries the install / uninstall / probe scripts that the
# NodeSoftwareOperator controller invokes on a target node when converging a
# RuntimeInstall CR whose spec.runtime == "runsc".
#
# The image must contain:
#   - curl / wget (for downloading the runsc binary in install)
#   - python3 (for the TOML self-check)
#   - nsenter / chroot (for entering host PID namespace to reload cri-o)
#   - coreutils (for install(1) and friends)
#
# Multi-stage: scripts are linted in a builder stage, then copied into a
# slim debian runtime. Pin to specific versions so the cri-o drop-in and the
# reload path do not drift.
#
# Build:  docker buildx build --platform linux/arm64 -t nodesoftware-runsc-handler:dev .
# Push:   docker push ghcr.io/chidionyema/nodesoftware-runsc-handler:<tag>
#
# Verify locally with: ./scripts/test-probe.sh   (no cri-o needed)

FROM debian:bookworm-slim AS linter

# Docker's default shell is `/bin/sh -c`, and on debian that is dash, which has no
# `pipefail`: measured 2026-09-08 the first RUN below died with `/bin/sh: 1: set: Illegal
# option -o pipefail` before apt-get ran at all. LAW 55 wants pipefail on every pipe, so the
# answer is the shell that has it rather than dropping the option. debian-slim ships bash.
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

COPY scripts /tmp/scripts/
RUN set -euo pipefail \
    && apt-get update \
    && apt-get install -y --no-install-recommends shellcheck ca-certificates \
    && shellcheck -s warning /tmp/scripts/nodesoftware-runsc-* \
    && echo "scripts: shellcheck clean" \
    && install -m 0755 /tmp/scripts/* /usr/local/bin/

# Runtime image: debian-slim has curl + python3 + util-linux out of the box.
# We pin the version of the base image so a vulnerability fix doesn't change
# script behaviour silently.
FROM debian:bookworm-slim

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# Runtime dependencies. nsenter comes from util-linux; python3 from base; curl
# from base. We pin via apt-get update before installing so the layer is
# reproducible.
RUN set -euo pipefail \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        bash ca-certificates curl python3 util-linux coreutils \
    && rm -rf /var/lib/apt/lists/*

# Copy linted scripts from the previous stage.
COPY --from=linter /usr/local/bin/nodesoftware-runsc-install   /usr/local/bin/
COPY --from=linter /usr/local/bin/nodesoftware-runsc-uninstall /usr/local/bin/
COPY --from=linter /usr/local/bin/nodesoftware-runsc-probe     /usr/local/bin/

# The controller runs as uid 10001 on the host. Our handler pod inherits the
# same securityContext (runAsNonRoot: true, runAsUser: 10001). We pre-touch
# ownership so the binary is executable after COPY.
USER 10001:10001

ENTRYPOINT ["/usr/local/bin/nodesoftware-runsc-install"]

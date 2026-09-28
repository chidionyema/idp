# nodesoftware-runsc-handler scripts — handler image for the runsc runtime.
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
# Build:  docker buildx build --platform linux/arm64 -t ghcr.io/chidionyema/runsc:dev .
# Push:   bin/dockerfiles publishes the multi-arch manifest list as
#         ghcr.io/chidionyema/runsc:main-<run>-<sha> (image name = dirname basename of the
#         Dockerfile). The NodeSoftwareOperator controller reads this tag from its own pod's
#         runsc-handler-mirror initContainer at startup (cmd/main.go:resolveHandlerImage),
#         so the same kustomize `images:` $imagepolicy marker that owns the controller
#         binary's tag (platform/image-automation/runsc.yaml) owns this tag too. A literal
#         IMAGE_TAG substitution has no place in this file; the controller's deployment.yaml
#         carries the marker.
#
# Verify locally with: ./scripts/test-probe.sh   (no cri-o needed)

FROM debian:bookworm-slim AS linter

# Docker's default shell is `/bin/sh -c`, and on debian that is dash, which has no
# `pipefail`. Measured 2026-09-08: this image has never been built. The build leg on the
# commit that landed it (93e4265e, run 34174722046) died on both stages with
# `/bin/sh: 1: set: Illegal option -o pipefail`, before apt-get ran at all, and every main
# run since has been green only because bin/dockerfiles builds the images a commit changed
# and nothing has touched this one. The tag platform/image-automation/runsc.yaml is wired
# to therefore does not exist in the registry.
#
# LAW 55 wants pipefail, so the answer is the shell that has it rather than dropping the
# option. debian-slim ships bash; each stage says so before its first RUN.
SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# --severity, not -s: shellcheck's -s is --shell, so `-s warning` asked it to lint for a
# shell named "warning" -- `Unknown shell: warning`, exit 4. Measured 2026-09-08: with
# that flag this stage has never linted anything. It failed before reaching the scripts,
# and the dash error one stage down hid that it had. The scripts are clean at this
# severity; the flag was the only thing wrong.
COPY scripts /tmp/scripts/
RUN set -euo pipefail \
    && apt-get update \
    && apt-get install -y --no-install-recommends shellcheck ca-certificates \
    && shellcheck --severity=warning /tmp/scripts/nodesoftware-runsc-* \
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

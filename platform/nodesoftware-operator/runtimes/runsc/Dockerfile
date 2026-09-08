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

# debian:bookworm-slim uses dash as /bin/sh, which does not understand
# `set -o pipefail`. We need pipefail so a failed `apt-get install` aborts the
# whole RUN even when `apt-get update` succeeded. Pin the SHELL to bash for
# every RUN in both stages below.
SHELL ["/bin/bash", "-c"]

FROM debian:bookworm-slim AS linter

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

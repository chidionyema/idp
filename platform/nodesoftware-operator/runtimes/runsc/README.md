# nodesoftware-runsc-handler — runtime handler image for spec.runtime == "runsc".
#
# This directory ships the install/uninstall/probe scripts that the
# NodeSoftwareOperator controller invokes on a target node when reconciling
# a `RuntimeInstall` CR. The controller's RBAC does NOT include `pods/exec`:
# it spawns a handler pod with the image referenced here, waits for the pod
# to terminate, then reads the logs.
#
# Files:
#   scripts/nodesoftware-runsc-install   (96 lines; bash; shellcheck + shfmt clean)
#   scripts/nodesoftware-runsc-uninstall (36 lines; bash; shellcheck + shfmt clean)
#   scripts/nodesoftware-runsc-probe     (32 lines; sh;  shellcheck + shfmt clean)
#   scripts/test-handler.sh              smoke test for exit codes
#   Dockerfile                           multi-stage, debian:bookworm-slim
#
# Reference contract:
#   /usr/local/bin/nodesoftware-runsc-install   <version> [host-root]
#   /usr/local/bin/nodesoftware-runsc-uninstall <version> [host-root]
#   /usr/local/bin/nodesoftware-runsc-probe
#
# The path /usr/local/bin/ is the contract. The controller's
# internal/handler/runsc/runsc.go hardcodes these paths; renaming the scripts
# (or moving them) is a contract break.
#
# Build:
#   docker buildx build --platform linux/arm64 \
#     -t ghcr.io/chidionyema/nodesoftware-runsc-handler:dev .
#
# The matching NODE-side handler image ref lives at:
#   ghcr.io/chidionyema/nodesoftware-runsc-handler:IMAGE_TAG
# IMAGE_TAG is substituted by Flux postBuild via Secret ghcr-pull.
# The deployment.yaml (in this directory's parent) overrides via
# `--handler-image=...` if pinning by tag isn't precise enough.
#
# Test:
#   ./scripts/test-handler.sh
#
# Empirical proof (milestone D): a real cluster drill on the canary node.

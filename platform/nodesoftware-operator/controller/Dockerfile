# Multi-stage Dockerfile for the NodeSoftwareOperator controller.
#
# Stage 1 (build): Go toolchain pulls controller-runtime + deps, builds a static binary.
# Stage 2 (runtime): distroless image with the binary + a nonroot user. The controller runs as
# 10001 (uid: 10001 is what the controller's Deployment securityContext expects per the
# platform/nodesoftware-operator/deployment.yaml in PR #2338).
#
# Build:    docker build -t ghcr.io/chidionyema/controller:IMAGE_TAG .
# Push:     the multi-arch manifest list lands at ghcr.io/chidionyema/controller:main-<run>-<sha>
#           (bin/dockerfiles derives the image name from the Dockerfile's dirname basename;
#           the deployment asks for ghcr.io/chidionyema/controller, the kustomize `images:`
#           block in platform/nodesoftware-operator/kustomization.yaml fills the tag via the
#           $imagepolicy marker in platform/image-automation/controller.yaml).
#
# Why `controller` and not `nodesoftware-operator`: every other image in this repo uses the
# dirname basename as its registry name (cyrus, hermes-agent, jit, lago-api, lago-front).
# `bin/dockerfiles` produces `ghcr.io/chidionyema/controller`; the deployment and kustomization
# both reference that exact name so there is one source of truth.
#
# IMAGE_TAG above is a placeholder for a human running these commands, not a substitution: the
# estate pins this image via a `$imagepolicy`-marked `newTag:` in kustomization.yaml, the same
# cyrus pattern every other in-repo image uses. The Flux row that previously claimed to
# substitute it from the ghcr-pull secret never could (that Secret's one key is
# `.dockerconfigjson`, not a legal envsubst variable name) and was removed on 2026-09-08
# (PR #2416); this PR replaces the broken mechanism with the working one.

FROM golang:1.26.3 AS build
WORKDIR /src

# Cache deps first (small layer, refreshed on go.mod/go.sum changes only).
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

# Build static binary.
COPY . .
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
    go build -trimpath -ldflags='-s -w' \
    -o /out/nodesoftware-operator ./cmd

# Runtime stage -- distroless, nonroot.
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/nodesoftware-operator /nodesoftware-operator
USER 10001:10001
ENTRYPOINT ["/nodesoftware-operator"]

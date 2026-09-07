# Multi-stage Dockerfile for the NodeSoftwareOperator controller.
#
# Stage 1 (build): Go toolchain pulls controller-runtime + deps, builds a static binary.
# Stage 2 (runtime): distroless image with the binary + a nonroot user. The controller runs as
# 10001 (uid: 10001 is what the controller's Deployment securityContext expects per the
# platform/nodesoftware-operator/deployment.yaml in PR #2338).
#
# Build:    docker build -t ghcr.io/chidionyema/nodesoftware-operator:IMAGE_TAG .
# Run:      docker run --rm ghcr.io/chidionyema/nodesoftware-operator:IMAGE_TAG
#
# The IMAGE_TAG placeholder is substituted at Flux postBuild from the ghcr-pull secret (idp#140
# image-automation). `optional: false` in the Flux row means a missing IMAGE_TAG fails the row,
# not a silent `:latest` rollout.

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

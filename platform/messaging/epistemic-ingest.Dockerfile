# idp#3448 CP1: the four ingestion connectors, one binary, one image.
#
# Named epistemic-ingest.Dockerfile (not a bare Dockerfile) because its build
# context has to be the whole platform/messaging module -- cmd/epistemic-ingest
# imports its sibling cloudevent/ and subject/ packages, and a Docker build
# context is exactly the Dockerfile's own directory (bin/dockerfiles: context
# = dirname(dockerfile)). A `<name>.Dockerfile` is named by its filename stem
# (bin/dockerfiles's own rule), which is what puts this image at
# ghcr.io/chidionyema/epistemic-ingest without moving cmd/demo's own Dockerfile
# story or duplicating go.mod into a directory of its own.
#
# Build:  docker build -f platform/messaging/epistemic-ingest.Dockerfile -t ghcr.io/chidionyema/epistemic-ingest platform/messaging
# Run:    epistemic-ingest github|slack|cicd|incidents  (platform/epistemic-fabric/ingest.yaml selects the mode per Deployment)

FROM golang:1.26.3 AS build
WORKDIR /src

COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod \
    go mod download

COPY . .
ARG TARGETOS
ARG TARGETARCH
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH \
    go build -trimpath -ldflags='-s -w' \
    -o /out/epistemic-ingest ./cmd/epistemic-ingest

# Runtime -- distroless, nonroot. uid/gid 10001 matches the Deployment's own
# securityContext (platform/epistemic-fabric/ingest.yaml), the same convention
# platform/nodesoftware-operator/controller/Dockerfile uses.
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /out/epistemic-ingest /epistemic-ingest
USER 10001:10001
ENTRYPOINT ["/epistemic-ingest"]

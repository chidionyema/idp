# voice-router: the estate's self-hosted streaming voice (ears + voice in-process,
# brain over the litellm router). Image: ghcr.io/chidionyema/voice-router
# (bin/dockerfiles names it after this directory). Built natively per arch by
# build-multiarch.yml: cgo against the sherpa-onnx shared libraries the Go module ships.
#
# Models are pinned by sha256 and baked in, so a pod never downloads at start:
#   ASR  nemo streaming fast-conformer 480ms int8   (measured 2026-09-26: word-perfect, endpoint +0.89s)
#   TTS  piper ljspeech medium, 22.05 kHz            (LJ Speech is public domain; lessac, the
#        faster-looking default, is research-only and bars voice-synthesis products)
# See docs/tickets/2026-09-26-voice-router-self-hosted.md for the measurements.

FROM debian:bookworm-slim AS models
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl bzip2 && rm -rf /var/lib/apt/lists/*
WORKDIR /models
RUN set -e; base=https://github.com/k2-fsa/sherpa-onnx/releases/download; \
    fetch() { curl -fsSL -o m.tar.bz2 "$base/$1" && echo "$2  m.tar.bz2" | sha256sum -c - && tar xjf m.tar.bz2 && rm m.tar.bz2; }; \
    fetch asr-models/sherpa-onnx-nemo-streaming-fast-conformer-transducer-en-480ms-int8.tar.bz2 da93061cbf7b708b6b65976f70b29f519be29df750d8cdcabf98c65645930f13; \
    fetch tts-models/vits-piper-en_US-ljspeech-medium.tar.bz2 3dfb4b759d8be032a4903a9538d128b0fda2a06ab1de6cbc2d93a97e2dd83dba

# The runtime copy: the releases' test recordings are for the build's tests, not the pod.
FROM models AS models-runtime
RUN rm -rf /models/*/test_wavs

FROM golang:1.27.1-bookworm AS build
ARG TARGETARCH
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download
COPY cmd ./cmd
COPY internal ./internal
# The binary's rpath points into the module cache; the libraries are copied out
# beside it in the same step, because the cache mount does not reach the image.
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    case "$TARGETARCH" in \
      amd64) triple=x86_64-unknown-linux-gnu ;; \
      arm64) triple=aarch64-unknown-linux-gnu ;; \
      *) echo "unsupported arch $TARGETARCH" >&2; exit 1 ;; \
    esac && \
    CGO_ENABLED=1 go vet ./... && \
    CGO_ENABLED=1 go build -trimpath -ldflags='-s -w' -o /out/voice-router ./cmd/voice-router && \
    mkdir -p /out/lib && \
    cp /go/pkg/mod/github.com/k2-fsa/sherpa-onnx-go-linux@*/lib/$triple/*.so /out/lib/
# Every test, against the models this image ships, on the arch it ships for: the
# ears on a human recording, the voice through the ears (word error rate), turn
# handling and barge-in. Nothing else in CI runs them. A skipped test here means
# a model went missing, so a skip fails the build.
RUN --mount=type=cache,target=/go/pkg/mod \
    --mount=type=cache,target=/root/.cache/go-build \
    --mount=type=bind,from=models,source=/models,target=/models \
    VOICE_MODELS=/models CGO_ENABLED=1 go test -count=1 -v ./... 2>&1 | tee /tmp/test.log && \
    ! grep -q -- '--- SKIP' /tmp/test.log && grep -q '^ok ' /tmp/test.log && ! grep -q '^FAIL' /tmp/test.log

FROM gcr.io/distroless/cc-debian12:nonroot
COPY --from=build /out/lib/ /usr/local/lib/voice-router/
COPY --from=build /out/voice-router /voice-router
COPY --from=models-runtime /models /models
ENV LD_LIBRARY_PATH=/usr/local/lib/voice-router \
    VOICE_MODELS=/models \
    VOICE_ADDR=:8080
USER 10001:10001
EXPOSE 8080
ENTRYPOINT ["/voice-router"]

# FleetView backend: serve.py mounts routes.py's envelopes over FastAPI/uvicorn. No third-party
# import beyond fastapi/uvicorn -- every sibling module (sessions.py, notes.py, signals.py,
# blast.py, graph.py, evals.py, mutations.py) is loaded by path from src/, resolved against
# __file__, so the whole directory travels together and nothing needs a package install step.
#
# blast.py loads bin/estate-twin-runtime as a module by path (SourceFileLoader) and calls its
# real blast_radius()/edges() -- it does not reimplement the graph walk (THE HEADLINE). That
# script lives at the repo root, outside backstage/plugins/fleetview-backend/, so this Dockerfile
# cannot use that directory as its build context (a Docker build can only COPY from its own
# context). estate-mcp.Dockerfile and estate-scheduler.Dockerfile hit the identical constraint
# for the same reason and both build from the repo root; this file does the same, and
# bin/dockerfiles names a root `<name>.Dockerfile` by its stem, so the image is still
# "fleetview-backend".
#
# The COPY destinations preserve the real repo's directory depth
# (backstage/plugins/fleetview-backend/src/*.py) because blast.py, graph.py, notes.py and
# signals.py all resolve `_ROOT = Path(__file__).resolve().parents[4]` themselves -- moving the
# source to a shallower path in the image would silently break that resolution.
#
# R24: this Dockerfile is discovered by bin/dockerfiles (a root `<name>.Dockerfile`, named by
# its stem) and built for both architectures by .github/workflows/build-multiarch.yml.
FROM docker.io/library/python:3.13-alpine
# nats-py is the third of these, and without it NATS_URL is decoration. `nats_adapter.py` raises
# RuntimeError("nats-py not installed") on both publish and subscribe, and `voice_media.publish`
# turns that into `{"published": false, "reason": "RuntimeError: nats-py not installed"}` -- a
# refusal this image would have returned on every event, honestly and for ever. Pinned like its
# neighbours; pure Python, no wheel to pick per architecture, so the multi-arch build is unaffected.
#
# NOT the speech models, but the `sovereign.voice` package that fronts them. The microphone moved to
# the browser (2026-09-26: POST /voice/hear carries PCM through the Backstage proxy to this
# sidecar), and voice_media.hear()/say()/stream() all start with `from sovereign.voice import
# engine, turnlog, catalogue` -- for the sample rate, the clause splitter and the turn log -- before
# they ask the router to transcribe or speak. Without the package every /voice/hear answered 500
# (ModuleNotFoundError: No module named 'sovereign') on 2026-10-08, so /face and /fleet heard
# nothing. The four files are stdlib at module level; faster-whisper, kokoro-onnx and numpy are
# imported lazily on the LOCAL engine path only, which this container never takes (250m CPU /
# 256Mi, read-only root) and which hear() already turns into a 502 naming the engine. The router
# does the speech here. Each file is named rather than the directory: sovereign/voice/static is a
# symlink out of this build context, and the image needs none of it.
#
# jsonschema, pyyaml and certifi are imported at module top by voice_media.py, voice_intents.py and
# voice.py, and httpx inside voice_media.py's cloud-voice synthesis. None was installed here, so
# on OKE every /voice/* route answered 500
# (ModuleNotFoundError) and the /fleet voice picker opened empty. estate_spatial.py and
# deploy_journeys.py are voice.py's two repo imports (stdlib only). This pip line and these COPYs
# are read by backstage/plugins/fleetview-backend/tests/test_image_imports.py, which imports every
# module against exactly them and fails the PR if one would not load in this image.
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn==0.34.0 nats-py==2.16.0 jsonschema==4.23.0 pyyaml==6.0.2 certifi==2025.8.3 httpx==0.28.1
COPY backstage/plugins/fleetview-backend/src /app/backstage/plugins/fleetview-backend/src
COPY bin/estate-twin-runtime /app/bin/estate-twin-runtime
COPY lib/estate_spatial.py /app/lib/estate_spatial.py
COPY mcp/plugins/deploy_journeys.py /app/mcp/plugins/deploy_journeys.py
COPY sovereign/__init__.py /app/sovereign/__init__.py
COPY sovereign/voice/__init__.py /app/sovereign/voice/__init__.py
COPY sovereign/voice/engine.py /app/sovereign/voice/engine.py
COPY sovereign/voice/turnlog.py /app/sovereign/voice/turnlog.py
COPY sovereign/voice/catalogue.py /app/sovereign/voice/catalogue.py
USER 10001
EXPOSE 18790
EXPOSE 8091
# platform/backstage/overlays/oke/kustomization.yaml runs this as a sidecar in the catalogue Pod,
# on 127.0.0.1, matching backstage/app-config.yaml's proxy.endpoints./fleetview target -- the
# proxy config does not change, only where 127.0.0.1:18790 is actually answered from.
#
# The fourth argv, 8091, is the mutations-relay port serve.py's own docstring documents
# (executor_link.py, /executor/poll and /executor/reply) -- 0.0.0.0-bound, unlike 18790, and
# reachable only through fleetview-executor-service.yaml's tailnet-exposed Service plus
# platform/tailscale/policy.hujson's deny-by-default ACL. A local `docker run` of this image
# (no FLEETVIEW_EXECUTOR_MODE set) still answers /mutations by calling mutations.py directly --
# opening this port costs nothing when nothing dials it.
#
# serve.py and routes.py moved into the fleetview_backend package (src/fleetview_backend/), whose
# modules import each other as `fleetview_backend.*`, so it runs as a module, as bin/serve-fleetview
# does. The path this used to name no longer exists: from 2026-09-27 every catalogue Pod rolled
# with this image crash-looped on "can't open file .../src/serve.py" and the catalogue never went
# Ready. serve.py takes `<port> [executor-port]`; the routes path argument is gone.
ENV PYTHONPATH=/app/backstage/plugins/fleetview-backend/src
ENTRYPOINT ["python3", "-m", "fleetview_backend.serve", "18790", "8091"]

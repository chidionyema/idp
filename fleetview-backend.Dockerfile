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
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn==0.34.0
COPY backstage/plugins/fleetview-backend/src /app/backstage/plugins/fleetview-backend/src
COPY bin/estate-twin-runtime /app/bin/estate-twin-runtime
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
ENTRYPOINT ["python3", "/app/backstage/plugins/fleetview-backend/src/serve.py", "18790", "/app/backstage/plugins/fleetview-backend/src/routes.py", "8091"]

# The warden job (crew#832 CP3): proves every vendor key and publishes metrics.
#
# A bare `Dockerfile` under platform/warden/ built with that directory as its own context
# (bin/dockerfiles' convention for a bare Dockerfile name) -- but the warden package needs
# platform/vendors/consoles.yaml (prove.py's VENDORS_PATH, a sibling directory) at runtime,
# which no context rooted at platform/warden can reach. This file lives at the repo root
# instead, alongside estate-mcp.Dockerfile/sovereign-worker.Dockerfile/
# estate-scheduler.Dockerfile, the existing pattern for an image whose sources cross
# directory boundaries, so its context is the whole repository.
FROM python:3.12-slim

WORKDIR /app

# Pinned to the same floors as sovereign/requirements.txt (prometheus_client>=0.19.0,
# pyyaml>=6.0, requests>=2.31) so the two sets of installs can't silently drift apart;
# warden does not need the rest of that file (cryptography, z3-solver, ...).
RUN pip install --no-cache-dir "prometheus_client>=0.19.0,<1" "PyYAML>=6.0,<7" "requests>=2.31,<3"

COPY platform/warden /app/warden
COPY platform/vendors /app/vendors

ENV PYTHONPATH=/app
ENTRYPOINT ["python", "-m", "warden.warden"]

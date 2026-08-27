# The sovereign Temporal worker, as it runs in the cluster (crew#396 step 2).
#
# Until 2026-08-26 the only worker was `python -m sovereign.engine.worker` under
# launchd on the Mac, polling a Temporal dev server on the same Mac. "Close the
# laptop" killed both. Step 1 (platform/temporal) moved the engine to the official
# chart; this image moves the worker next to it. bin/dockerfiles lists this file,
# build-multiarch.yml pushes ghcr.io/chidionyema/sovereign-worker:main-<run>-<sha>
# for amd64 and arm64, and platform/image-automation/sovereign-worker.yaml rolls
# the Deployment in platform/temporal/worker.yaml on every main build.
#
# Build context is the repository root (bin/dockerfiles: context = dirname). Step 3
# (crew#396, sovereign/engine/kini.py) runs each KINI checkpoint's bdd files inside this
# image, so it carries features/ (sovereign/pytest.ini: bdd_features_base_dir = ..), bin/
# and platform/ that those tests read, and requirements-dev.txt (pytest, pytest-bdd).
# /app is the working directory; the package imports itself as `sovereign.*`.
# The same Python CI runs (ci.yml: 3.12). .dockerignore keeps .venv and .git out.
FROM docker.io/python:3.12-slim
WORKDIR /app
COPY sovereign/requirements.txt sovereign/requirements-dev.txt /app/sovereign/
RUN pip install --no-cache-dir -r /app/sovereign/requirements-dev.txt \
 && useradd --system --uid 10001 --create-home sovereign
COPY sovereign /app/sovereign
# sovereign/policy.py reads the living policy from AGENTS.md one directory above itself
# and refuses to start without it (crew#396: 18 restarts, PolicyError: cannot read /app/AGENTS.md).
COPY AGENTS.md /app/AGENTS.md
COPY features /app/features
COPY bin /app/bin
COPY platform /app/platform
# require-ro-rootfs: the worker writes only under ESTATE_HOME (config.ensure_dirs);
# the Deployment mounts an emptyDir there and sets HOME to it.
ENV ESTATE_HOME=/tmp/estate HOME=/tmp PYTHONUNBUFFERED=1
USER sovereign
CMD ["python", "-m", "sovereign.engine.worker"]

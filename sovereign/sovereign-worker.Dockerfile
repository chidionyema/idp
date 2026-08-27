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
# Build context is the sovereign/ directory (bin/dockerfiles: context = dirname);
# the package imports itself as `sovereign.*`, so it is copied under /app/sovereign
# and /app is the working directory. The same Python CI runs (ci.yml: 3.12).
FROM docker.io/python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/sovereign/requirements.txt
RUN pip install --no-cache-dir -r /app/sovereign/requirements.txt \
 && useradd --system --uid 10001 --create-home sovereign
COPY . /app/sovereign
# require-ro-rootfs: the worker writes only under ESTATE_HOME (config.ensure_dirs);
# the Deployment mounts an emptyDir there and sets HOME to it.
ENV ESTATE_HOME=/tmp/estate HOME=/tmp PYTHONUNBUFFERED=1
USER sovereign
CMD ["python", "-m", "sovereign.engine.worker"]

# The event spine, as it runs in the cluster.
#
# One image, two commands: the bridge (NATS in, Temporal signals out) and the observer
# (the Temporal side, serving the workflow that verifies a reconcile). One build and one
# tag, so the two halves cannot drift apart -- a bridge that signals a workflow nobody
# serves is a bus with nobody listening.
#
# Build context is the repository root (bin/dockerfiles: context = dirname), and the
# package is copied whole so the image carries exactly the code the estate's gate graded.
#
# Two dependencies, both already the estate's: temporalio is the pin the sovereign worker
# runs (sovereign/requirements.txt: temporalio==1.32.0) and nats-py is what the estate's
# Python services use to reach the event bus.
FROM docker.io/python:3.12-slim
ARG TARGETARCH
# The base floats, so its packages move under the build (sovereign-worker.Dockerfile records
# the same reasoning): upgrade so the image carries the security pocket of the suite it was
# built from.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY spine /app/spine
COPY spine/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --no-compile -r /app/requirements.txt
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp
USER 10001
ENTRYPOINT ["python", "-m", "spine"]

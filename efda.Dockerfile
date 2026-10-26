# The universal coverage layer, as it runs in the cluster.
#
# One program, several commands: the controller and the executor are the same
# binary with different arguments, so there is one build and one tag to roll.
# The package is pure standard library on purpose -- the estate's gate speaks
# Python, and a coverage layer that cannot be tested offline is a coverage
# layer nobody trusts.
#
# kubectl is here for the same reason estate-mcp carries it: the controllers
# read and write through the same door the estate already trusts, with the
# estate's own credentials, and there is no second credential path.
#
# Build context is the repository root (bin/dockerfiles: context = dirname).
FROM docker.io/python:3.12-slim
ARG TARGETARCH
# The base floats, so its packages move under the build (sovereign-worker.Dockerfile
# records the same reasoning): upgrade so the image carries the security pocket
# of the suite it was built from.
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN kubectl_version="$(curl -fsSL https://dl.k8s.io/release/stable.txt)" \
 && curl -fsSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/${kubectl_version}/bin/linux/${TARGETARCH}/kubectl" \
 && chmod 0755 /usr/local/bin/kubectl
WORKDIR /app
COPY efda /app/efda
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp
USER 10001
ENTRYPOINT ["python", "-m", "efda"]

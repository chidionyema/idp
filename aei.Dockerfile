# The estate's execution-intelligence collector.
#
# WHY THE ROOT CONTEXT. bin/dockerfiles names an image by its Dockerfile's file stem and gives it
# the context of the Dockerfile's directory, so an image that carries the AEI package (which
# lives in packages/aei, not under platform/) must be built from the repository root -- the same
# shape efda.Dockerfile, factory.Dockerfile and spine.Dockerfile already use. The rebuild is
# still scoped: bin/dockerfiles computes a rebuild from the files a Dockerfile actually COPYs, so
# a change anywhere else in the estate does not rebuild this image.
#
# WHAT IS IN IT. The AEI package, verbatim -- the collector, the client, the contract and the
# analysis -- and the viewer the collector serves. No copy of the source: the image builds the
# same tree the laptop runs, so the laptop's ledger and the cluster's ledger speak one contract.
#
# THE DEPENDENCY. psycopg, the Postgres driver, and nothing else. The collector is stdlib-only
# apart from that one driver, and it is deliberately small: 128Mi of request, a SQLite file or
# one estate database, and no message queue, because the estate has one Postgres and one router
# and a collector that needed a broker would be a new estate layer rather than a collector.
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/chidionyema/idp" \
      org.opencontainers.image.title="estate execution intelligence collector" \
      org.opencontainers.image.description="The AEI collector: observes execution, appends it to the estate's own Postgres, serves it back."

# psycopg only. The collector's own code is stdlib.
RUN pip install --no-cache-dir "psycopg[binary]>=3.1"

WORKDIR /app
# The package. Copied, never vendored: an image that carried a second copy of the collector
# would be a second implementation of the same contract, which is the thing this repo forbids.
COPY packages/aei/src/aei /app/aei
# The viewer, served by the collector at /. It sits one level above the package, which is where
# the server looks for it.
COPY packages/aei/viewer.html /app/viewer.html

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app

# Non-root, matching the pod's runAsUser 65532 (platform/observability/aei.yaml). An image
# that needs root to start cannot run under the policy its Deployment applies.
RUN useradd --uid 65532 --no-create-home --shell /usr/sbin/nologin aei
USER 65532:65532

# Assert, AS THE POD'S OWN USER, that the collector imports and that the Postgres driver is
# there. The pod's readiness probe is an exec probe, so a missing driver would show up as a
# crashloop rather than as a clear build failure -- this is the cheaper place to find it.
RUN python -c "import os, aei.server, aei.pgstore, psycopg; \
    assert os.getuid() == 65532, 'this check must run as the pod user'; \
    print('aei imports clean as uid', os.getuid())"

ENTRYPOINT ["python", "-m", "aei.server"]
CMD ["--host", "0.0.0.0", "--port", "8766", "--store", "postgres"]

EXPOSE 8766

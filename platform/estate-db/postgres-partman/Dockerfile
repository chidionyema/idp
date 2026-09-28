# The estate's own Postgres image: the CloudNativePG standard 18 image, plus pg_partman,
# with the base Debian packages patched so the image passes the build-multiarch Trivy gate.
#
# WHY pg_partman: lago (commerce) runs `CREATE EXTENSION pg_partman` in its DB migration; the
# CNPG standard image lacks it (measured), so lago-migrate-db fails 42501-ish
# `extension "pg_partman" is not available`.
#
# WHY apt-get upgrade after install: the CNPG base (ghcr.io/cloudnative-pg/postgresql:
# 18.1-standard-bookworm) carries upstream critical CVEs (libssl3, libgnutls30 — reported by the
# build-multiarch Trivy scan 2026-09-08). apt-get upgrade pulls the patched Debian packages so
# this image does not inherit them.
FROM ghcr.io/cloudnative-pg/postgresql:18.1-standard-bookworm

USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        postgresql-18-partman \
    # Patch the base's critical CVEs (libssl3 / libgnutls30) so the image passes the Trivy gate.
    && DEBIAN_FRONTEND=noninteractive apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# Gate: pg_partman must be provably installed (a wrong package name fails here, not in a later
# migration), and print its real paths for the follow-up cluster.yaml imageName flip.
RUN dpkg -L postgresql-18-partman | grep -E '\.(control|sql|so)$' \
    && echo "pg_partman installed:" && dpkg -L postgresql-18-partman | grep partman.control
USER postgres

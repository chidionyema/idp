# The estate's own Postgres image: the CloudNativePG standard 18 image, plus pg_partman.
#
# WHY: lago (commerce) runs `CREATE EXTENSION pg_partman` in its DB migration, but the CNPG
# standard image ships only pgaudit/pgvector/pg-failover-slots — no pg_partman .so/.control
# (measured). lago-migrate-db fails `extension pg_partman is not available`.
#
# The CNPG image already configures the PGDG apt source (bookworm-pgdg), so installing the
# matching pg_partman package is one apt line — no base rebuild.
FROM ghcr.io/cloudnative-pg/postgresql:18.1-standard-bookworm

# postgresql-18-partman from PGDG (the CNPG base is Debian 12 / PG 18).
USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        postgresql-18-partman \
    && rm -rf /var/lib/apt/lists/*
# Diagnostic: name exactly which files the package installed so the estate-pg follow-up (the
# cluster.yaml imageName flip) and any consumer know the real extension path. dpkg -L returns a
# nonzero only if the package truly is not installed, so this is also the install gate.
RUN dpkg -L postgresql-18-partman | grep -E '\.(control|sql|so)$' \
    && echo "pg_partman installed:" && dpkg -L postgresql-18-partman | grep partman.control
USER postgres

# The estate's own Postgres image: the CloudNativePG standard 18 image, plus pg_partman.
#
# WHY: lago (commerce) runs `CREATE EXTENSION pg_partman` in its DB migration, but the CNPG
# standard image ships only pgaudit/pgvector/pg-failover-slots — it has no pg_partman .so or
# .control (measured 2026-09-08: `pg_available_extensions` has no partman; no partman* under
# /usr/lib/postgresql/18/lib or /usr/share/postgresql/18/extension). lago-migrate-db fails
# `extension "pg_partman" is not available` and commerce can never install.
#
# The CNPG image already configures the PGDG apt source (bookworm-pgdg, /usr/share/postgresql
# -common), so installing the matching pg_partman package is one apt line — no base rebuild.
#
# Keep the base tag identical to what cluster.yaml points at (18.1-standard-bookworm) so the
# only delta this image adds is pg_partman; upgrading this image is a normal CNPG image bump.
FROM ghcr.io/cloudnative-pg/postgresql:18.1-standard-bookworm

# postgresql-18-partman from PGDG; the "standard" Debian install is the base CNPG container.
USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        postgresql-18-partman \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get purge -y --auto-remove \
    && find /var/log -type f -name "*.log" -delete -o -type f -name "*.gz" -delete 2>/dev/null || true
USER postgres

# Verify the extension is now present so a wrong build fails fast at image build, not in a later
# CREATE EXTENSION during a migration.
RUN test -f /usr/share/postgresql/18/extension/partman.control \
    && test -f /usr/lib/postgresql/18/lib/partman.so \
    && echo "pg_partman present:" && ls /usr/share/postgresql/18/extension/partman* | head -3

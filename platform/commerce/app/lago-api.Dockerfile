# Lago API, Sidekiq workers, clock and the migrate Job, as a non-root user (crew#623).
# Upstream getlago/api ships no USER line (crane config, 2026-09-05: User empty), so every
# pod the chart renders from it runs as root and the cluster's restricted PodSecurity
# profile refuses it: "runAsNonRoot != true" on lago-migrate-db, 2026-09-05. Founder,
# 2026-09-05: hold the pod security standard, no Kyverno exception for commerce
# (~/.claude/docs/founder/2026-09-05T1243Z-the-immediate-clear-agent-driven-the-agent-has-8539b2f6.md).
# This image changes nothing but who the process is and which directories it may write:
# Puma's pidfile is tmp/pids/server.pid (config/puma.rb), bootsnap writes tmp/cache, Rails
# logs to log/, and the chart mounts the invoice PVC at /app/storage (fsGroup 1000 in
# lago.yaml makes that one writable). The tag must match the chart's appVersion:
# lago-1.28.0 renders getlago/api:v1.33.4.
FROM docker.io/getlago/api:v1.33.4
RUN groupadd --gid 1000 lago \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin lago \
    && mkdir -p /app/tmp/pids /app/tmp/cache /app/log /app/storage \
    && chown -R lago:lago /app/tmp /app/log /app/storage
# Bundler and Rails resolve ~ for caches and config; /tmp is the only writable home a
# non-root process without a home directory can rely on.
ENV HOME=/tmp
USER 1000:1000

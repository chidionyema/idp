# Lago API, Sidekiq workers, clock and the migrate Job, as a non-root user (crew#623).
# Upstream getlago/api ships no USER line (crane config, 2026-09-05: User empty), so every
# pod the chart renders from it runs as root and the cluster's restricted PodSecurity
# profile refuses it: "runAsNonRoot != true" on lago-migrate-db, 2026-09-05. Founder,
# 2026-09-05: hold the pod security standard, no Kyverno exception for commerce
# (~/.claude/docs/founder/2026-09-05T1243Z-the-immediate-clear-agent-driven-the-agent-has-8539b2f6.md).
# This image changes nothing but who the process is and which directories it may write:
# Puma's pidfile is tmp/pids/server.pid (config/puma.rb), bootsnap writes tmp/cache, Rails
# logs to log/, and the chart mounts the invoice PVC at /app/storage (fsGroup 1000 in
# lago.yaml makes that one writable). The tag is the one lago.yaml's `version:` value
# tells the chart to render; the chart's own default (v1.33.4) carries activestorage
# 8.0.2.1 (CVE-2026-33195, CRITICAL) and build-multiarch refuses it (run 33967534541).
# Stage 1: the json gem the base pins as a Ruby default gem is 2.18.0 (CVE-2026-33210,
# CRITICAL, fixed in 2.19.2). It is a C extension and the runtime image carries no
# compiler, so it is built here and only its three artefacts cross into the final image.
FROM docker.io/getlago/api:v1.52.1 AS json-gem
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && gem install json -v 2.19.2 --no-document \
    && cd "$(gem env gemdir)" \
    && mkdir -p /out \
    && cp -a --parents gems/json-2.19.2 specifications/json-2.19.2.gemspec extensions/*/*/json-2.19.2 /out/

FROM docker.io/getlago/api:v1.52.1
# The scan that gates this image also fails the base on libgnutls30t64 (CVE-2026-33845),
# which Debian security already ships fixed; upgrading takes whatever the base is behind on.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# The built json 2.19.2 lands in the bundle path; the default 2.18.0 (its gemspec, and the
# stdlib copy that would otherwise win on $LOAD_PATH) is removed so `require "json"`
# activates the fixed gem. pdfcpu is a Go binary the base ships for invoice PDFs; its
# golang.org/x/crypto is CVE-2026-56854 (CRITICAL) and this estate renders no PDFs
# (lago.yaml: LAGO_DISABLE_PDF_GENERATION), so the binary goes rather than the gate.
COPY --from=json-gem /out/ /usr/local/bundle/
RUN rubylib="$(ruby -e 'puts RbConfig::CONFIG["rubylibdir"]')" \
    && archlib="$(ruby -e 'puts RbConfig::CONFIG["archdir"]')" \
    && find / -xdev -path '*/specifications/default/json-2.18.0.gemspec' -delete \
    && rm -rf "$rubylib/json" "$rubylib/json.rb" "$archlib/json" \
    && rm -f /usr/local/bin/pdfcpu \
    && check='require "json"; abort "json #{JSON::VERSION} still loads" unless JSON::VERSION == "2.19.2"; puts "json #{JSON::VERSION}"' \
    && ruby -e "$check" \
    && cd /app && bundle exec ruby -e "$check"
RUN groupadd --gid 1000 lago \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin lago \
    && mkdir -p /app/tmp/pids /app/tmp/cache /app/log /app/storage \
    && chown -R lago:lago /app/tmp /app/log /app/storage
# Bundler and Rails resolve ~ for caches and config; /tmp is the only writable home a
# non-root process without a home directory can rely on.
ENV HOME=/tmp
USER 1000:1000

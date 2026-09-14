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
FROM docker.io/getlago/api:v1.52.1
# THE BASE'S SECURITY POCKET, AND WHY THIS LINE DID NOT TAKE IT. This file shipped with
# `apt-get upgrade -y --no-install-recommends`, and on 2026-09-13 the image failed the
# "no CRITICAL vulnerability ships" step of build-multiarch.yml with twelve CRITICALs:
#
#   libperl5.40, perl, perl-base, perl-modules-5.40
#     CVE-2026-13221  CVE-2026-42496  CVE-2026-8376
#   installed 5.40.1-6, fixed 5.40.1-6+deb13u1
#
# The fix is a Debian point release in the security pocket, and `--no-install-recommends` is
# what kept it out: perl-base Recommends perl-modules-5.40, and an upgrade forbidden from
# pulling its own modules holds the whole set back rather than installing a torn combination.
# `apt-get upgrade` therefore reported success while changing nothing -- the same shape as a
# gate that exits 0 while the thing it grades is wrong.
#
# The two Dockerfiles beside this one that carry the identical three CVEs,
# estate-mcp.Dockerfile and sovereign-worker.Dockerfile, never had the flag: their comment
# records the same upstream rebuild and their `apt-get upgrade -y` takes the pocket. This one
# now matches them.
#
# The same line also takes libgnutls30t64 (CVE-2026-33845), which Debian security already
# ships fixed and which is the reason the upgrade was added here in the first place.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*
# The base pins json 2.18.0 as a Ruby default gem (CVE-2026-33210, CRITICAL) while the app's
# bundle already carries json 2.21.2, which is what `require "json"` loads under bundler
# (build-multiarch run on 1cc2eb85: "json 2.21.2"). The default gemspec and the stdlib copy
# are dead weight the scan reads; they go, and the build proves the loaded version is fixed.
# pdfcpu is a Go binary the base ships for invoice PDFs; its golang.org/x/crypto is
# CVE-2026-56854 (CRITICAL) and this estate sets LAGO_DISABLE_PDF_GENERATION, so it goes too.
RUN rubylib="$(ruby -e 'puts RbConfig::CONFIG["rubylibdir"]')" \
    && archlib="$(ruby -e 'puts RbConfig::CONFIG["archdir"]')" \
    && find / -xdev -path '*/specifications/default/json-2.18.0.gemspec' -delete \
    && rm -rf "$rubylib/json" "$rubylib/json.rb" "$archlib/json" \
    && rm -f /usr/local/bin/pdfcpu \
    && cd /app && bundle exec ruby -e 'require "json"; v = Gem::Version.new(JSON::VERSION); abort "json #{v} still loads" if v < Gem::Version.new("2.19.2"); puts "json #{v}"'
RUN groupadd --gid 1000 lago \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin lago \
    && mkdir -p /app/tmp/pids /app/tmp/cache /app/log /app/storage \
    && chown -R lago:lago /app/tmp /app/log /app/storage
# Bundler and Rails resolve ~ for caches and config; /tmp is the only writable home a
# non-root process without a home directory can rely on.
ENV HOME=/tmp
USER 1000:1000

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
# The scan that gates this image also fails the base on libgnutls30t64 (CVE-2026-33845),
# which Debian security already ships fixed; upgrading takes whatever the base is behind on.
# idp#8655: the GHCR layer cache replays an unchanged upgrade, so a published fix never arrived;
# a new value here (build-multiarch passes the UTC date) re-runs the layer below.
ARG OS_PACKAGES_AS_OF=2026-11-27
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
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
# CVE-2026-122006 (GHSA-f3w6-w445-fwh9, CRITICAL): activestorage < 8.0.5.2 allows arbitrary file
# write and read in image analysis, and v1.52.1 locks Rails 8.0.5.1. The 8.0 line's own patch
# release fixes it, so no Lago 1.52 -> 1.57 upgrade (Rails 8.1, five schema releases) is needed
# (idp#8658). Rails 8.0.5.2's one dependency change sets the rest of the closure: actionview asks
# rails-html-sanitizer >= 1.7.2, which asks loofah >= 2.25.3, which asks nokogiri >= 1.19.5.
# lago-api-gem-patch.rb rewrites Gemfile.lock from the fetched gems' own specs and refuses a lock
# any dependency line would break. The replaced versions are uninstalled so the scan reads only
# what loads, and the last command proves what bundler loads.
COPY lago-api-gem-patch.rb /tmp/gem-patch.rb
RUN mkdir /tmp/gems && cd /tmp/gems \
    && for g in actioncable actionmailbox actionmailer actionpack actiontext actionview activejob \
         activemodel activerecord activestorage activesupport rails railties; do \
         gem fetch "$g" --version 8.0.5.2 || exit 1; done \
    && gem fetch rails-html-sanitizer --version 1.7.2 \
    && gem fetch loofah --version 2.25.3 \
    && gem fetch nokogiri --version 1.19.5 \
    && cd /app \
    && ruby /tmp/gem-patch.rb Gemfile.lock /tmp/gems > /tmp/gems-replaced \
    && gem install --local --no-document --ignore-dependencies /tmp/gems/*.gem \
    && while read -r name version; do \
         gem uninstall --ignore-dependencies --executables "$name" --version "$version" || exit 1; done < /tmp/gems-replaced \
    && rm -rf /tmp/gems /tmp/gem-patch.rb /tmp/gems-replaced \
    && bundle check \
    && bundle exec ruby -e 'want = { "activestorage" => "8.0.5.2", "actionview" => "8.0.5.2", "rails-html-sanitizer" => "1.7.2", "loofah" => "2.25.3", "nokogiri" => "1.19.5" }; bad = want.reject { |n, v| Gem.loaded_specs[n] && Gem.loaded_specs[n].version.to_s == v && Gem::Specification.find_all_by_name(n).map { |s| s.version.to_s }.uniq == [v] }; abort "not the only, loaded version: #{bad}" unless bad.empty?; require "active_storage"; require "nokogiri"; puts "patched #{want}"'
RUN groupadd --gid 1000 lago \
    && useradd --uid 1000 --gid 1000 --no-create-home --shell /usr/sbin/nologin lago \
    && mkdir -p /app/tmp/pids /app/tmp/cache /app/log /app/storage \
    && chown -R lago:lago /app/tmp /app/log /app/storage
# Bundler and Rails resolve ~ for caches and config; /tmp is the only writable home a
# non-root process without a home directory can rely on.
ENV HOME=/tmp
USER 1000:1000

# Cyrus agent orchestration image (crew#834).
# Base: Node 18+ with git, gh, jq.
# Installs: cyrus CLI.
# Note: No upstream Docker image exists - this is built from source or CLI install.
FROM node:20-slim

# Install system dependencies
# `upgrade` is not decoration: the scan that gates this image fails the base on
# libgnutls30 3.7.9-2+deb12u6 (CVE-2026-33845), and Debian security already ships
# 3.7.9-2+deb12u7. Upgrading takes whatever the base image is behind on.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    jq \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install the GitHub CLI from its own release tarball. The apt repository at cli.github.com
# publishes no arm64 index, so the apt route builds on amd64 and fails on arm64.
ARG GH_VERSION=2.100.0
RUN arch="$(dpkg --print-architecture)" \
    && curl -fsSL -o /tmp/gh.tgz "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${arch}.tar.gz" \
    && tar -xzf /tmp/gh.tgz -C /tmp \
    && install -m 0755 "/tmp/gh_${GH_VERSION}_linux_${arch}/bin/gh" /usr/local/bin/gh \
    && rm -rf /tmp/gh.tgz "/tmp/gh_${GH_VERSION}_linux_${arch}"

# npm 10 bundles tar 6.2.1, which the scan fails on (CVE-2026-59873, a gzip-bomb
# denial of service). npm 11 bundles tar 7.x, so upgrading npm is the fix, and it
# has to happen before anything else is installed with it. The version is pinned
# to 11 rather than latest: npm 12 requires node 22 or newer, and this base is
# node 20, so `npm@latest` fails the build with EBADENGINE.
RUN npm install -g npm@11

# Install Cyrus CLI globally
ARG CYRUS_VERSION=latest
RUN npm install -g "cyrus-ai@${CYRUS_VERSION}"

# cyrus-ai depends on the `cloudflared` npm package, which downloads a Go binary at install
# time so cyrus can open its own tunnel for webhooks. This estate has one ingress door, the
# gateway, and a second one is not a thing we are willing to have present, let alone running.
# That binary is also the third critical the scan finds: golang.org/x/crypto v0.53.0,
# CVE-2026-56854 in the ssh package.
#
# The binary goes and the JavaScript stays. Deleting the whole package was the first attempt
# and it built an image that could not start: cyrus-cloudflare-tunnel-client imports
# 'cloudflared' at the top of dist/CloudflareTunnelClient.js, unconditionally, so node exited
# with ERR_MODULE_NOT_FOUND on boot, before any transport was chosen, and every pod sat in
# CrashLoopBackOff behind a green build. The JavaScript is inert without its binary:
# cloudflared/lib/constants.js resolves the executable to `<pkg>/bin/cloudflared` and nothing
# reads that path unless a tunnel is actually opened, which webhook transport never does.
#
# The `node --input-type=module` line is the guard, not decoration. It is the exact failure
# the running pod hit, run at build time, so this image can never again leave the builder
# unable to resolve a package cyrus imports on its first line.
RUN set -eux; \
    find /usr/local/lib/node_modules -type d -path '*/node_modules/cloudflared/bin' -prune -exec rm -rf {} +; \
    test ! -e /usr/local/lib/node_modules/cyrus-ai/node_modules/cloudflared/bin; \
    cd /usr/local/lib/node_modules/cyrus-ai; \
    node --input-type=module -e "await import('cloudflared'); console.log('cloudflared resolves, binary gone')"

# Configure git user for commits
RUN git config --global user.name "estate-bot" && \
    git config --global user.email "estate-agents[bot]@users.noreply.github.com"

# Create directories for worktrees and repos
RUN mkdir -p /worktrees /repo

# Set working directory
WORKDIR /app

# The entrypoint turns the vault's mounted files into the environment cyrus reads and
# makes the configured checkouts exist. `entrypoint.sh clone` is the init container's
# job; with no argument it execs cyrus. Its header carries the measurement that made it
# necessary: cyrus 0.2.71 reads no *_FILE credential variable.
COPY entrypoint.sh /usr/local/bin/cyrus-entrypoint
RUN chmod 0755 /usr/local/bin/cyrus-entrypoint \
    && bash -n /usr/local/bin/cyrus-entrypoint

ENTRYPOINT ["/usr/local/bin/cyrus-entrypoint"]
CMD []

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
# has to happen before anything else is installed with it.
RUN npm install -g npm@latest

# Install Cyrus CLI globally
ARG CYRUS_VERSION=latest
RUN npm install -g "cyrus-ai@${CYRUS_VERSION}"

# cyrus-ai bundles a cloudflared binary to open its own tunnel for webhooks. This
# estate has one ingress door, the gateway, and a second one is not a thing we are
# willing to have present, let alone running. Deleting it also removes the third
# critical the scan finds: golang.org/x/crypto v0.53.0, CVE-2026-56854 in the ssh
# package. Webhooks reach Cyrus through the gateway, so nothing here uses it.
RUN rm -rf /usr/local/lib/node_modules/cyrus-ai/node_modules/cloudflared

# Configure git user for commits
RUN git config --global user.name "estate-bot" && \
    git config --global user.email "estate-agents[bot]@users.noreply.github.com"

# Create directories for worktrees and repos
RUN mkdir -p /worktrees /repo

# Set working directory
WORKDIR /app

# Default command runs Cyrus
CMD ["cyrus"]

# Cyrus agent orchestration image (crew#834).
# Base: Node 18+ with git, gh, jq.
# Installs: cyrus CLI.
# Note: No upstream Docker image exists - this is built from source or CLI install.
FROM node:20-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    jq \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install the GitHub CLI from its own release tarball. The apt repository at cli.github.com
# publishes no arm64 index, so the apt route builds on amd64 and fails on arm64.
ARG GH_VERSION=2.63.2
RUN arch="$(dpkg --print-architecture)" \
    && curl -fsSL -o /tmp/gh.tgz "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${arch}.tar.gz" \
    && tar -xzf /tmp/gh.tgz -C /tmp \
    && install -m 0755 "/tmp/gh_${GH_VERSION}_linux_${arch}/bin/gh" /usr/local/bin/gh \
    && rm -rf /tmp/gh.tgz "/tmp/gh_${GH_VERSION}_linux_${arch}"

# Install Cyrus CLI globally
ARG CYRUS_VERSION=latest
RUN npm install -g "cyrus-ai@${CYRUS_VERSION}"

# Configure git user for commits
RUN git config --global user.name "estate-bot" && \
    git config --global user.email "estate-agents[bot]@users.noreply.github.com"

# Create directories for worktrees and repos
RUN mkdir -p /worktrees /repo

# Set working directory
WORKDIR /app

# Default command runs Cyrus
CMD ["cyrus"]

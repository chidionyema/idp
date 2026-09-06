#!/usr/bin/env bash
# Turn the vault's mounted files into the environment cyrus reads, make the configured
# checkouts exist, then exec cyrus. Why each of those is necessary, with the measurement
# that proved it: platform/cyrus/README.md, "What the manifest claimed and the pod did".
set -euo pipefail
on_exit() {
	local rc=$?
	[ "$rc" -eq 0 ] || echo "cyrus-entrypoint: exit $rc" >&2
}
trap on_exit EXIT

GH_TOKEN_PATH=${CYRUS_GH_TOKEN_PATH:-/secrets/github/CYRUS_GITHUB_TOKEN}
WEBHOOK_DIR=${CYRUS_WEBHOOK_SECRET_DIR:-/secrets/webhook}

# A missing file is announced and left unset, never defaulted: an empty
# GITHUB_WEBHOOK_SECRET silently downgrades that transport to proxy mode, and a
# credential that quietly becomes "" is the failure this file exists to end.
export_file() {
	if [ -r "$2" ]; then
		export "$1=$(cat "$2")"
	else
		echo "cyrus-entrypoint: $2 is not readable, $1 stays unset" >&2
	fi
}

export_file GITHUB_TOKEN "$GH_TOKEN_PATH"
export_file LINEAR_API_TOKEN "$WEBHOOK_DIR/linear-api-token"
export_file LINEAR_WEBHOOK_SECRET "$WEBHOOK_DIR/linear-webhook-secret"
export_file GITHUB_WEBHOOK_SECRET "$WEBHOOK_DIR/github-webhook-secret"

# git authenticates through an askpass file rather than a URL or a command line: a token
# in argv is readable by anything that can run `ps` (LAW 10). The helper cats the file on
# every invocation, so the App installation token -- rewritten every ten minutes, valid
# for an hour -- is never captured stale.
ASKPASS=${TMPDIR:-/tmp}/cyrus-askpass
printf '#!/bin/sh\ncat %s\n' "$GH_TOKEN_PATH" >"$ASKPASS"
chmod 0700 "$ASKPASS"
export GIT_ASKPASS="$ASKPASS"
export GIT_TERMINAL_PROMPT=0

# Without a username git asks for that first and the helper answers it with the token,
# which fails as a 403 that reads like a permissions problem rather than a protocol one.
git config --global credential."https://github.com".username x-access-token
git config --global user.name "estate-bot"
git config --global user.email "estate-agents[bot]@users.noreply.github.com"
git config --global --add safe.directory '*'

# Cyrus never clones: GitService runs `git worktree add` with cwd set to repositoryPath
# and reports `<path> is not a git repository` when it is absent (GitService.js:476),
# while /repo is an emptyDir that starts empty on every restart.
clone_repos() {
	local config=$1 path url
	[ -r "$config" ] || {
		echo "cyrus-entrypoint: no config at $config, nothing to clone" >&2
		return 0
	}
	while IFS=$'\t' read -r path url; do
		[ -n "$path" ] && [ -n "$url" ] || continue
		if [ -d "$path/.git" ]; then
			echo "cyrus-entrypoint: $path already a checkout, fetching"
			git -C "$path" fetch --quiet --all --prune
		else
			# Blobless partial clone: full history, so `git worktree add` reaches any
			# branch, without downloading every file of every past revision.
			echo "cyrus-entrypoint: cloning $url into $path"
			git clone --quiet --filter=blob:none "$url" "$path"
		fi
	done < <(jq -r '.repositories[] | select(.isActive != false)
	                | "\(.repositoryPath)\t\(.githubUrl)"' "$config")
}

# ~/.cyrus has to be made by this uid, not by kubelet: a subPath mount at
# ~/.cyrus/config.json leaves the directory root-owned and cyrus dies creating
# mcp-configs beside it. The config is a copy, not a link: cyrus rewrites config.json
# in place after its allowedTools migration (Application.js, "[Migration] Added
# \"Skill\""), and a link into the read-only ConfigMap dies with EROFS on that write.
# A ConfigMap change reaches cyrus on the next start, when the copy is taken again.
CONFIG_SRC=${CYRUS_CONFIG_JSON:-/etc/cyrus/config.json}
copy_config() {
	mkdir -p "$HOME/.cyrus"
	[ -r "$CONFIG_SRC" ] || {
		echo "cyrus-entrypoint: no config at $CONFIG_SRC" >&2
		return 0
	}
	rm -f "$HOME/.cyrus/config.json"
	cp "$CONFIG_SRC" "$HOME/.cyrus/config.json"
	chmod 0600 "$HOME/.cyrus/config.json"
}

case "${1:-}" in
clone)
	clone_repos "$CONFIG_SRC"
	echo "cyrus-entrypoint: checkouts ready"
	;;
*)
	copy_config
	exec cyrus "$@"
	;;
esac

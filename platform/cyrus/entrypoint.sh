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
# The Linear OAuth client (external-secret.yaml, 3). Both are read by `cyrus self-auth` to mint
# the access token and by EdgeWorker to refresh it; absent, the pod stays on the GitHub door.
OAUTH_DIR=${CYRUS_LINEAR_OAUTH_DIR:-/secrets/linear-oauth}
export_file LINEAR_CLIENT_ID "$OAUTH_DIR/client-id"
export_file LINEAR_CLIENT_SECRET "$OAUTH_DIR/client-secret"

# git authenticates through an askpass file rather than a URL or a command line: a token
# in argv is readable by anything that can run `ps` (LAW 10). The helper cats the file on
# every invocation, so the App installation token -- rewritten every ten minutes, valid
# for an hour -- is never captured stale.
ASKPASS=${TMPDIR:-/tmp}/cyrus-askpass
printf '#!/bin/sh\ncat %s\n' "$GH_TOKEN_PATH" >"$ASKPASS"
chmod 0700 "$ASKPASS"
export GIT_ASKPASS="$ASKPASS"
export GIT_TERMINAL_PROMPT=0

# gh takes the same road. GH_TOKEN outranks GITHUB_TOKEN inside gh, so a wrapper first on PATH
# reads the file on every call and the boot-time export above only serves code that reads the
# variable once. Without this a pod that now lives for days (Reloader no longer rolls it on
# every mint, see external-secret.yaml) would hand gh an installation token that expired an
# hour after boot.
GH_WRAP=${TMPDIR:-/tmp}/cyrus-bin
mkdir -p "$GH_WRAP"
printf '#!/bin/sh\nGH_TOKEN=$(cat %s) exec %s "$@"\n' "$GH_TOKEN_PATH" "$(command -v gh)" >"$GH_WRAP/gh"
chmod 0700 "$GH_WRAP/gh"
export PATH="$GH_WRAP:$PATH"

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
# mcp-configs beside it. The ConfigMap stays at its own read-only path and the config is
# linked in, so a ConfigMap change still reaches cyrus through the link.
CONFIG_SRC=${CYRUS_CONFIG_JSON:-/etc/cyrus/config.json}
link_config() {
	mkdir -p "$HOME/.cyrus"
	[ -r "$CONFIG_SRC" ] || {
		echo "cyrus-entrypoint: no config at $CONFIG_SRC" >&2
		return 0
	}
	# A copy, not a symlink: cyrus migrates its own config on boot and writes it back, and a
	# symlink into the read-only ConfigMap made that an EROFS exit (README, wall 6). Refreshed
	# every start, so git stays the source of truth.
	# What the previous boot held: the OAuth token `cyrus self-auth` saved, or the one cyrus
	# refreshed and wrote back. The home volume is a claim, so the old copy is still here; it is
	# read before the copy overwrites it and joined back after, so a consent is given once.
	local kept='{}'
	if [ -r "$HOME/.cyrus/config.json" ]; then
		kept=$(jq -c '[.linearWorkspaces // {} | to_entries[] | select(.value.linearToken != null)] | from_entries' \
			"$HOME/.cyrus/config.json" 2>/dev/null || echo '{}')
	fi
	cp "$CONFIG_SRC" "$HOME/.cyrus/config.json"
	chmod 0600 "$HOME/.cyrus/config.json"
	if [ "$kept" != '{}' ]; then
		local tmp
		tmp=$(mktemp "$HOME/.cyrus/config.XXXXXX")
		jq --argjson kept "$kept" '.linearWorkspaces = ((.linearWorkspaces // {}) + $kept)' \
			"$HOME/.cyrus/config.json" >"$tmp"
		mv "$tmp" "$HOME/.cyrus/config.json"
		chmod 0600 "$HOME/.cyrus/config.json"
		echo "cyrus-entrypoint: kept the OAuth token(s) for $(jq -r '.linearWorkspaces | length' "$HOME/.cyrus/config.json") workspace(s)"
	else
		join_linear_token "$HOME/.cyrus/config.json"
	fi
}

# No OAuth token yet and a client to mint one with: `cyrus self-auth` listens on the serving
# port for the consent redirect (https://<CYRUS_BASE_URL>/callback), exchanges the code with
# the client secret and saves the token into config.json. It prints the consent URL to the
# pod log; the founder opens it once. Bounded: after the window the pod comes up on the GitHub
# door as before, and the next restart opens the window again.
SELF_AUTH_WINDOW=${CYRUS_SELF_AUTH_WINDOW:-30m}
mint_linear_token() {
	local config=$1
	[ -n "${LINEAR_CLIENT_ID:-}" ] && [ -n "${LINEAR_CLIENT_SECRET:-}" ] || return 0
	if [ "$(jq -r '[.linearWorkspaces // {} | .[] | select(.linearToken != null)] | length' "$config")" != "0" ]; then
		return 0
	fi
	echo "cyrus-entrypoint: no Linear OAuth token yet; waiting up to $SELF_AUTH_WINDOW for the founder's consent"
	if timeout "$SELF_AUTH_WINDOW" cyrus self-auth; then
		echo "cyrus-entrypoint: Linear OAuth token saved"
	else
		echo "cyrus-entrypoint: no consent within $SELF_AUTH_WINDOW; starting on the GitHub door" >&2
	fi
}

# The only road cyrus offers for a Linear token is config.linearWorkspaces[<id>].linearToken
# (cyrus-core config-schemas.js; no environment variable is read). The ConfigMap in git
# carries the workspace id and never the token; the token is joined here, from the mounted
# vault file, into the pod's private copy. Every workspace id the repositories name gets
# the one token. A missing file is announced and joins nothing (README, wall 7).
LINEAR_TOKEN_PATH=${CYRUS_LINEAR_TOKEN_PATH:-$WEBHOOK_DIR/linear-api-token}
join_linear_token() {
	local config=$1 tmp
	if [ ! -r "$LINEAR_TOKEN_PATH" ]; then
		echo "cyrus-entrypoint: $LINEAR_TOKEN_PATH is not readable, linearWorkspaces stays unset" >&2
		return 0
	fi
	tmp=$(mktemp "$(dirname "$config")/config.XXXXXX")
	jq --rawfile tok "$LINEAR_TOKEN_PATH" '
		([.repositories[]? | .linearWorkspaceId // empty] | unique) as $ids
		| .linearWorkspaces = ((.linearWorkspaces // {})
			+ ($ids | map({key: ., value: {linearToken: ($tok | rtrimstr("\n"))}}) | from_entries))
	' "$config" >"$tmp"
	mv "$tmp" "$config"
	chmod 0600 "$config"
	echo "cyrus-entrypoint: linearWorkspaces joined for $(jq -r '.linearWorkspaces | length' "$config") workspace(s)"
}

case "${1:-}" in
clone)
	clone_repos "$CONFIG_SRC"
	echo "cyrus-entrypoint: checkouts ready"
	;;
*)
	link_config
	mint_linear_token "$HOME/.cyrus/config.json"
	exec cyrus "$@"
	;;
esac

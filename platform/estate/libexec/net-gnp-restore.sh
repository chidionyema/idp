#!/usr/bin/env bash
# net-gnp-restore -- MUTATING. Re-create a GlobalNetworkPolicy from a net-gnp-orphan-remove snapshot.
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.rd/bin:$PATH"
case "$1" in "$HOME/.estate/state/snapshots/gnp-"*.json) ;; *) echo "REFUSED not a net-gnp snapshot: $1"; exit 1;; esac
kubectl --request-timeout=30s create -f "$1"

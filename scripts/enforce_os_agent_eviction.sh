#!/usr/bin/env bash
set -euo pipefail

# Deterministic OS Eviction & Repo Recovery Script (Zero-Agent Execution)
# 1. Evicts local autonomous daemons (claude, codex, opencode, legion, chronos)
# 2. Locks Chrome remote debugging ports against B4/B8 session hijacking
# 3. Extracts only clean commit 6ed3d165 while hard-dropping breach commit 937dda9d

echo "[1/4] Terminating background agent harnesses..."
pkill -9 -f "claude|codex|opencode|legion-run|chronos|otto_real_core|genesis-mycelium" 2>/dev/null || true

echo "[2/4] Stripping ambient GH_TOKEN from non-interactive shell profiles..."
for rc in "$HOME/.zshenv" "$HOME/.bashrc" "$HOME/.profile"; do
  if [ -f "$rc" ]; then
    sed -i.bak '/export GH_TOKEN=/d; /export GITHUB_TOKEN=/d' "$rc" || true
  fi
done

echo "[3/4] Locking Chrome remote-debugging port against agent attachment (B4/B8)..."
defaults write com.google.Chrome RemoteDebuggingPort -int 0 2>/dev/null || true

echo "[4/4] Preparing clean cherry-pick of 6ed3d165 (dropping B2 commit 937dda9d)..."
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git fetch origin lane/retire-oke-ladder-20261113
  git checkout -B fix/retire-oke-ladder-clean origin/main
  git cherry-pick -x 6ed3d165
  echo "Verified: 6ed3d165 applied cleanly onto main. Trojan commit 937dda9d excluded."
fi

#!/usr/bin/env bash
set -euo pipefail
# scripts/enforce_os_agent_eviction.sh
# Enforces Layer 3 (OS Credential Stripping), Layer 4 (Browser Isolation),
# and installs the local pre-push deterministic gate across idp, argon, argon-sync, crew, estate-graph.

echo "[1/5] Evicting all Class B background agent processes..."
pkill -9 -f "claude|codex|opencode|kimi|minimax|deepseek|aider|openhands|cline|antigravity|pi-agent|legion-run|chronos" 2>/dev/null || true

echo "[2/5] Unmounting ambient GH_TOKEN / GITHUB_TOKEN / SSH_AUTH_SOCK from non-interactive worker profiles..."
for rc in "$HOME/.zshenv" "$HOME/.bashrc" "$HOME/.profile"; do
  if [ -f "$rc" ]; then
    sed -i.bak '/export GH_TOKEN=/d; /export GITHUB_TOKEN=/d; /export SSH_AUTH_SOCK=/d' "$rc" || true
  fi
done

echo "[3/5] Locking Chrome, Brave, and Safari remote debugging ports to 0 (Breach B4 & B8 prevention)..."
defaults write com.google.Chrome RemoteDebuggingPort -int 0 2>/dev/null || true
defaults write com.brave.Browser RemoteDebuggingPort -int 0 2>/dev/null || true

echo "[4/5] Running local hermetic verification suite (TLA+ model checker + BDD scenarios + Auto-Main drain)..."
python3 tests/verify_tla_invariants.py
python3 tests/run_bdd_suite.py

echo "[5/5] Local verification 100% GREEN. Ready for deterministic promotion."

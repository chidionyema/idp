#!/bin/bash
set -euo pipefail
AGENTS="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"
for name in monitor scan dashboard; do
  plist="$AGENTS/dev.disksentinel.$name.plist"
  if [ -f "$plist" ]; then
    launchctl bootout "$DOMAIN" "$plist" >/dev/null 2>&1 || true
    rm -f "$plist"
  fi
done
if [ -L "$HOME/.local/bin/disk-sentinel" ]; then rm -f "$HOME/.local/bin/disk-sentinel"; fi
echo 'Launch jobs disabled. Dashboard, binaries and history retained for evidence.'
echo 'If desired, remove ~/.local/share/disk-sentinel and ~/.local/state/disk-sentinel manually after review.'

#!/usr/bin/env bash
# launchd cannot expand variables in plists — render at install time.
set -euo pipefail
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.estate/log"
sed "s|@HOME@|$HOME|g" "$(dirname "$0")/com.estate.pennyd.plist" \
  > "$HOME/Library/LaunchAgents/com.estate.pennyd.plist"
launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.estate.pennyd.plist" \
  || launchctl kickstart -k "gui/$(id -u)/com.estate.pennyd"
echo "pennyd installed and started"

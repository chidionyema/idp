#!/usr/bin/env bash
# The menu bar dot (R2/R3, master spec 2.1). SwiftBar plugin.
#
# SwiftBar (https://github.com/swiftbar/SwiftBar) is the mature menu bar
# host: it runs this script every 5 seconds (the ".5s" in the filename)
# and draws whatever it prints. No daemon of ours runs; this script only
# reads the state file the kernel writes (sovereign/presence/state.py).
#
# Install: symlink this file into the SwiftBar plugin folder:
#   ln -s "$(pwd)/sovereign/presence/swiftbar/estate-presence.5s.sh" "<SwiftBar plugin folder>/"
# ESTATE_HOME is read the same way sovereign/config.py reads it: the
# environment, else ~/.estate. Nothing else is typed here (LAW 46).
#
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
set -euo pipefail

ESTATE_HOME="${ESTATE_HOME:-$HOME/.estate}"
STATE_FILE="${SB_PRESENCE_STATE_FILE:-$ESTATE_HOME/sovereign/presence.json}"
IDP="$(cd "$(dirname "$(readlink "$0" || echo "$0")")/../../.." && pwd)"

dot="grey"
state="ghost"
if [ -r "$STATE_FILE" ]; then
  # one JSON object per file, written by state.write(); the two fields are
  # plain strings so a grep is enough and no runtime is launched every 5s.
  dot="$(sed -n 's/.*"dot": *"\([^"]*\)".*/\1/p' "$STATE_FILE" | head -1)"
  state="$(sed -n 's/.*"state": *"\([^"]*\)".*/\1/p' "$STATE_FILE" | head -1)"
  dot="${dot:-grey}"; state="${state:-ghost}"
fi

# Title line: the dot. Ghost and Haptic are the same grey; no pixel changes.
echo "● | color=$dot"
echo "---"
echo "presence: $state"
echo "Open Spatial | bash='$IDP/bin/sb' param1=presence param2=--json terminal=false"
echo "Estate status | bash='$IDP/bin/sb' param1=status terminal=true"
echo "Digest | bash='$IDP/bin/sb' param1=digest terminal=true"

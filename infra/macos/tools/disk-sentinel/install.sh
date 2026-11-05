#!/bin/bash
# Disk Sentinel installer for macOS. No sudo, package manager or shell profile edits.
set -euo pipefail
umask 077

if [ "$(uname -s)" != Darwin ]; then
  echo 'BLOCKED: this installer requires macOS. The monitor can still be tested with Bash.' >&2
  exit 1
fi

SRC="$(cd "$(dirname "$0")" && pwd)"
DST="$HOME/.local/share/disk-sentinel"
STATE="$HOME/.local/state/disk-sentinel"
AGENTS="$HOME/Library/LaunchAgents"
BIN="$HOME/.local/bin"
UID_NUM="$(id -u)"
DOMAIN="gui/$UID_NUM"

[ -r "$SRC/sentinel.sh" ] || { echo 'BLOCKED: sentinel.sh is missing next to installer' >&2; exit 1; }
/bin/bash -n "$SRC/sentinel.sh" || { echo 'BLOCKED: invalid Bash syntax' >&2; exit 1; }

FREE_KB="$(/bin/df -kP "$HOME" | /usr/bin/awk 'NR==2 {print $4}')"
if [ -z "$FREE_KB" ] || [ "$FREE_KB" -lt 2048 ]; then
  cat >&2 <<'TEXT'
BLOCKED: less than 2 MiB available. Do not run broad cleanup commands.
Inspect with read-only commands first:
  df -h "$HOME"
  du -sh "$HOME/.npm" "$HOME/.nvm/.cache" "$HOME/Library/Developer" "$HOME/Library/Caches" 2>/dev/null
Free some space using the responsible application's documented cleanup facility,
then rerun this installer. No files have been deleted.
TEXT
  exit 1
fi

mkdir -p "$DST" "$STATE" "$AGENTS" "$BIN"
chmod 700 "$DST" "$STATE"

if [ -e "$DST/sentinel.sh" ]; then
  cp -p "$DST/sentinel.sh" "$DST/sentinel.sh.previous" || true
fi
install -m 700 "$SRC/sentinel.sh" "$DST/sentinel.sh"
if [ -e "$BIN/disk-sentinel" ] && [ ! -L "$BIN/disk-sentinel" ]; then
  echo "BLOCKED: existing non-symlink at $BIN/disk-sentinel; not overwriting." >&2
  exit 1
fi
if [ -L "$BIN/disk-sentinel" ] && [ "$(readlink "$BIN/disk-sentinel")" != "$DST/sentinel.sh" ]; then
  echo 'BLOCKED: disk-sentinel is already a symlink to another installation. Refusing to replace it.' >&2
  exit 1
fi
ln -sfn "$DST/sentinel.sh" "$BIN/disk-sentinel"

# Require successful telemetry and dashboard generation before creating launch jobs.
"$DST/sentinel.sh" tick || { echo 'BLOCKED: first monitor tick failed. No jobs registered.' >&2; exit 1; }

# The plists are tracked next to this installer, not built from a heredoc here: bin/idp-inventory
# marks a loaded job MANAGED only when a file named <label>.plist is tracked in a repository, and
# a second copy of the definition is exactly how the declared job and the running job drift.
write_job() {
  local name="$1"
  local template="$SRC/launchd/dev.disksentinel.$name.plist"
  local plist="$AGENTS/dev.disksentinel.$name.plist"
  local home_escaped
  [ -r "$template" ] || { echo "BLOCKED: tracked plist missing: $template" >&2; exit 1; }
  home_escaped=$(printf '%s' "$HOME" | /usr/bin/sed 's/[&|\\]/\\&/g')
  /usr/bin/sed "s|\${HOME}|$home_escaped|g" "$template" > "$plist"
  chmod 644 "$plist"
  plutil -lint "$plist" >/dev/null || { echo "BLOCKED: invalid plist $plist" >&2; exit 1; }
}

# Reload only our own jobs.
for name in monitor scan dashboard; do
  job="$AGENTS/dev.disksentinel.$name.plist"
  [ -f "$job" ] && launchctl bootout "$DOMAIN" "$job" >/dev/null 2>&1 || true
done

write_job monitor
write_job scan
write_job dashboard

for name in monitor scan dashboard; do
  job="$AGENTS/dev.disksentinel.$name.plist"
  if ! launchctl bootstrap "$DOMAIN" "$job"; then
    echo "BLOCKED: could not bootstrap $name; login session may not expose a GUI launchd domain" >&2
    exit 1
  fi
  launchctl print "$DOMAIN/dev.disksentinel.$name" >/dev/null || { echo "BLOCKED: $name not registered" >&2; exit 1; }
done

printf '\nPASS: Disk Sentinel installed and registered.\n'
printf 'Dashboard: %s\n' "$DST/dashboard.html"
printf 'Monitor: every 60 seconds; inventory: daily at 03:15; browser: opens at login.\n'
printf 'Commands (absolute-path, unaffected by PATH problems):\n'
printf '  "%s/sentinel.sh" status\n' "$DST"
printf '  "%s/sentinel.sh" scan\n' "$DST"
printf '  "%s/sentinel.sh" review\n' "$DST"

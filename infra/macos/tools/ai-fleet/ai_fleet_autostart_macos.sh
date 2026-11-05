#!/bin/bash
# macOS AI Fleet: install, status, disable; no sudo or shell-profile modifications.
set -Eeuo pipefail
trap 'rc=$?; echo "ERROR at line $LINENO (exit $rc). Changes may be partial; check status and logs." >&2' ERR
umask 077

MODE=${1:-install}
BASE="$HOME/Library/Application Support/AI Fleet"
AGENTS="$HOME/Library/LaunchAgents"
LOGS="$HOME/Library/Logs/AI Fleet"
UID_NUM=$(id -u)
LABEL_DSH=local.aifleet.dsh
LABEL_GUI=local.aifleet.gui
LABEL_KIMI=local.aifleet.kimiweb
# CLI launchers often need Node's bin directory even when the login shell did not load nvm.
RUN_PATH="$HOME/.local/opt/dsh-standalone/node/bin:$HOME/.nvm/versions/node/v24.22.2/bin:$HOME/.nvm/versions/node/v26.13.0/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export PATH="$RUN_PATH:$PATH"

fatal() { printf 'BLOCKED: %s\n' "$*" >&2; exit 1; }
plist_escape() { printf '%s' "$1" | /usr/bin/sed -e 's/\&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/"/\&quot;/g'; }
app_path() {
  local name path match
  for name in "$@"; do
    for path in "/Applications/$name.app" "$HOME/Applications/$name.app"; do
      if [ -d "$path/Contents" ]; then printf '%s\n' "$path"; return 0; fi
    done
    # Spotlight fallback for apps installed outside /Applications.
    if [ -x /usr/bin/mdfind ]; then
      match=$(/usr/bin/mdfind "kMDItemFSName == \"$name.app\"" 2>/dev/null | /usr/bin/head -n 1 || true)
      if [ -n "$match" ] && [ -d "$match/Contents" ]; then printf '%s\n' "$match"; return 0; fi
    fi
  done
  return 1
}
find_cli() {
  local name=$1 c
  for c in "$HOME/.local/opt/dsh-standalone/bin/$name" \
           "$HOME/.local/bin/$name" "/usr/local/bin/$name" "/opt/homebrew/bin/$name" \
           "$HOME/.nvm/versions/node/"*/bin/"$name"; do
    [ -x "$c" ] || continue
    if "$c" --version >/dev/null 2>&1; then printf '%s\n' "$c"; return 0; fi
  done
  c=$(command -v "$name" || true)
  if [ -n "$c" ] && "$c" --version >/dev/null 2>&1; then printf '%s\n' "$c"; return 0; fi
  return 1
}
write_plist() {
  local label=$1 command=$2 logname=$3 kind=$4 path="$AGENTS/$label.plist"
  local escaped_command escaped_label escaped_stdout escaped_stderr
  escaped_command=$(plist_escape "$command")
  escaped_label=$(plist_escape "$label")
  escaped_stdout=$(plist_escape "$LOGS/$logname.out.log")
  escaped_stderr=$(plist_escape "$LOGS/$logname.err.log")
  cat > "$path" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$escaped_label</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$escaped_command</string><string>$kind</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$escaped_stdout</string>
  <key>StandardErrorPath</key><string>$escaped_stderr</string>
  <key>WorkingDirectory</key><string>$(plist_escape "$HOME")</string>
  <key>Umask</key><integer>63</integer>
XML
  if [ "$kind" = "gui" ]; then
    cat >> "$path" <<XML
  <key>StartInterval</key><integer>60</integer>
XML
  else
    cat >> "$path" <<XML
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>60</integer>
XML
  fi
  printf '</dict></plist>\n' >> "$path"
  /usr/bin/plutil -lint "$path" >/dev/null
  chmod 600 "$path"
}
boot_agent() {
  local label=$1 path="$AGENTS/$1.plist"
  /bin/launchctl bootout "gui/$UID_NUM" "$path" >/dev/null 2>&1 || true
  /bin/launchctl enable "gui/$UID_NUM/$label" >/dev/null 2>&1 || true
  /bin/launchctl bootstrap "gui/$UID_NUM" "$path"
}
status_agent() {
  local label=$1
  if /bin/launchctl print "gui/$UID_NUM/$label" >/dev/null 2>&1; then
    printf 'REGISTERED  %s\n' "$label"
    /bin/launchctl print "gui/$UID_NUM/$label" 2>/dev/null | /usr/bin/grep -E 'state =|last exit code =|runs =' | /usr/bin/head -n 4 || true
  else
    printf 'NOT LOADED %s\n' "$label"
  fi
}

case "$MODE" in
  status)
    for label in "$LABEL_DSH" "$LABEL_GUI" "$LABEL_KIMI"; do status_agent "$label"; done
    if [ -e "$BASE/dsh.path" ]; then
      DSH=$(cat "$BASE/dsh.path")
      if "$DSH" --version >/dev/null 2>&1; then echo 'DSH CLI: working'; else echo 'DSH CLI: BROKEN'; fi
    fi
    echo "Logs: $LOGS"
    exit 0 ;;
  disable)
    for label in "$LABEL_DSH" "$LABEL_GUI" "$LABEL_KIMI"; do
      /bin/launchctl bootout "gui/$UID_NUM" "$AGENTS/$label.plist" >/dev/null 2>&1 || true
      rm -f "$AGENTS/$label.plist"
    done
    echo 'AI Fleet automatic startup disabled; existing apps are not terminated.'
    exit 0 ;;
  install) ;;
  *) fatal 'Usage: bash ai_fleet_autostart_macos.sh [install|status|disable]' ;;
esac

[ "$(uname -s)" = Darwin ] || fatal 'This installer runs on macOS only.'
[ -x /usr/bin/plutil ] || fatal 'macOS plutil unavailable.'

mkdir -p "$BASE" "$AGENTS" "$LOGS"
chmod 700 "$BASE" "$LOGS"

# Resolve app bundles; never assume the user's app names or paths.
KIMI_APP=$(app_path 'Kimi Code' 'Kimi Code Desktop' || true)
CODEX_APP=$(app_path 'ChatGPT' 'Codex' || true)
CLAUDE_APP=$(app_path 'Claude' || true)
DSH_CLI=$(find_cli dsh || true)
KIMI_CLI=''
if [ -z "$KIMI_APP" ]; then KIMI_CLI=$(find_cli kimi || true); fi

printf 'Detected:\n  Kimi desktop: %s\n  Codex desktop: %s\n  Claude desktop: %s\n  DSH CLI: %s\n  Kimi CLI fallback: %s\n' \
  "${KIMI_APP:-missing}" "${CODEX_APP:-missing}" "${CLAUDE_APP:-missing}" "${DSH_CLI:-missing/broken}" "${KIMI_CLI:-not required}"

# Fail the whole preflight if any of the four cannot be served. No partial installation.
[ -n "$DSH_CLI" ] || fatal 'DSH is still broken. Run dsh --version successfully before enabling autostart.'
[ -n "$CODEX_APP" ] || fatal 'ChatGPT (with Codex) or Codex.app is not installed in a discoverable location.'
[ -n "$CLAUDE_APP" ] || fatal 'Claude.app is not installed in a discoverable location.'
[ -n "$KIMI_APP" ] || [ -n "$KIMI_CLI" ] || fatal 'Neither Kimi Code Desktop nor Kimi Code CLI is installed.'
if [ -z "$KIMI_APP" ]; then
  "$KIMI_CLI" web --help >/dev/null 2>&1 || fatal 'Installed Kimi CLI does not support kimi web.'
fi

# Configuration written as plain lines, never shell-evaluated.
printf '%s\n' "$DSH_CLI" > "$BASE/dsh.path"
printf '%s\n' "$KIMI_APP" > "$BASE/kimi.app"
printf '%s\n' "$CODEX_APP" > "$BASE/codex.app"
printf '%s\n' "$CLAUDE_APP" > "$BASE/claude.app"
printf '%s\n' "$KIMI_CLI" > "$BASE/kimi.path"
chmod 600 "$BASE"/*

# Install reusable helper; launchd runs it through /bin/bash (does not require its executable bit).
HELPER="$BASE/supervise.sh"
cat > "$HELPER" <<'HELPER_SCRIPT'
#!/bin/bash
set -euo pipefail
BASE="$HOME/Library/Application Support/AI Fleet"
LOGS="$HOME/Library/Logs/AI Fleet"
export PATH="$HOME/.local/opt/dsh-standalone/node/bin:$HOME/.nvm/versions/node/v24.22.2/bin:$HOME/.nvm/versions/node/v26.13.0/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
mode=${1:-}
app_running() {
  local app=$1 exe
  exe=$(/usr/libexec/PlistBuddy -c 'Print CFBundleExecutable' "$app/Contents/Info.plist" 2>/dev/null || true)
  [ -n "$exe" ] || return 1
  /usr/bin/pgrep -x "$exe" >/dev/null 2>&1 && return 0
  /bin/ps -axo command= | /usr/bin/grep -F "$app/Contents/MacOS/$exe" | /usr/bin/grep -v '/usr/bin/grep' >/dev/null 2>&1 && return 0
  return 1
}
ensure_open() {
  local app=$1 tag=$2
  [ -d "$app/Contents" ] || { echo "Missing GUI bundle: $app" >&2; return 1; }
  if ! app_running "$app"; then
    /usr/bin/open -g -a "$app" || return 1
    # Navigate to the coding interface only on launch/recovery.
    # These URLs create a blank draft, not an agent task.
    if [ "$tag" = claude ]; then
      /usr/bin/open -g 'claude://code/new' || true
    elif [ "$tag" = codex ]; then
      /usr/bin/open -g 'codex://threads/new' || true
    fi
  fi
}
case "$mode" in
  dsh)
    cli=$(cat "$BASE/dsh.path")
    [ -x "$cli" ] || { echo 'DSH CLI missing, reinstall it' >&2; exit 1; }
    exec "$cli" web
    ;;
  kimiweb)
    cli=$(cat "$BASE/kimi.path")
    [ -x "$cli" ] || { echo 'Kimi CLI missing' >&2; exit 1; }
    exec "$cli" web
    ;;
  gui)
    rc=0
    for name in kimi codex claude; do
      app=$(cat "$BASE/$name.app")
      [ -n "$app" ] || continue
      ensure_open "$app" "$name" || rc=1
    done
    exit "$rc"
    ;;
  *) echo 'Unknown supervisor mode' >&2; exit 2 ;;
esac
HELPER_SCRIPT
chmod 700 "$HELPER"

for n in dsh gui kimi; do
  touch "$LOGS/$n.out.log" "$LOGS/$n.err.log"
  chmod 600 "$LOGS/$n.out.log" "$LOGS/$n.err.log"
done

# First boot: GUI polling runs on login + every 60s. DSH is kept running by launchd.
write_plist "$LABEL_DSH" "$HELPER" dsh dsh
write_plist "$LABEL_GUI" "$HELPER" gui gui
if [ -z "$KIMI_APP" ]; then
  write_plist "$LABEL_KIMI" "$HELPER" kimi kimiweb
else
  /bin/launchctl bootout "gui/$UID_NUM" "$AGENTS/$LABEL_KIMI.plist" >/dev/null 2>&1 || true
  rm -f "$AGENTS/$LABEL_KIMI.plist"
fi

boot_agent "$LABEL_DSH"
boot_agent "$LABEL_GUI"
if [ -z "$KIMI_APP" ]; then boot_agent "$LABEL_KIMI"; fi

# launchctl bootstrap confirms registration, not service readiness.
echo
status_agent "$LABEL_DSH"
status_agent "$LABEL_GUI"
if [ -z "$KIMI_APP" ]; then status_agent "$LABEL_KIMI"; fi

echo
printf 'Installed login-time supervisors. Logs: %s\n' "$LOGS"
printf 'Check DSH startup: tail -n 30 "%s/dsh.err.log" "%s/dsh.out.log"\n' "$LOGS" "$LOGS"
printf 'Check status: bash "%s" status\n' "$0"
printf 'Disable: bash "%s" disable\n' "$0"
echo 'NOTE: launchd registration does not prove DSH reached its listening/ready state.'

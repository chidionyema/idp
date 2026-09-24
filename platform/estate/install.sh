#!/usr/bin/env bash
# estate installer — runs executor from source tree. State lives in ~/.estate.
# Supports: macOS (launchd), Linux (systemd).
# Usage:
#   install.sh              install/upgrade
#   install.sh --doctor     diagnose
#   install.sh --uninstall remove service, keep state
#   install.sh --dry-run   show plan, do nothing
set -eo pipefail

VERSION="0.1.0"
SRC_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STATE_DIR="${ESTATE_HOME:-$HOME/.estate}"
LOG_FILE="$STATE_DIR/install.log"
PLIST_DIR="$HOME/Library/LaunchAgents"
SYSTEMD_DIR="$HOME/.config/systemd/user"
BIN_DIR="$HOME/bin"

MODE="install"
case "${1:-}" in
  --doctor)     MODE="doctor" ;;
  --uninstall)  MODE="uninstall" ;;
  --dry-run)    MODE="dryrun" ;;
  --help|-h)
    sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'
    exit 0 ;;
esac

mkdir -p "$STATE_DIR"
: >> "$LOG_FILE"
c_blue='\033[1;34m'; c_green='\033[1;32m'; c_yellow='\033[1;33m'; c_red='\033[1;31m'; c_off='\033[0m'
say()  { printf "${c_blue}→${c_off} %s\n" "$*" | tee -a "$LOG_FILE"; }
ok()   { printf "${c_green}✓${c_off} %s\n" "$*" | tee -a "$LOG_FILE"; }
warn() { printf "${c_yellow}!${c_off} %s\n" "$*" | tee -a "$LOG_FILE"; }
fail() { printf "${c_red}✗${c_off} %s\n" "$*" | tee -a "$LOG_FILE" >&2; exit 1; }
hdr()  { printf "\n${c_blue}== %s ==${c_off}\n" "$*" | tee -a "$LOG_FILE"; }

# ---- preflight -----------------------------------------------------------
preflight() {
  hdr "preflight"
  local avail_kb
  avail_kb=$(df -k "$HOME" | awk 'NR==2 {print $4}')
  if [ "$avail_kb" -lt 204800 ]; then
    fail "less than 200MB free ($(( avail_kb / 1024 )) MB)"
  fi
  ok "disk: $(( avail_kb / 1024 )) MB free"
  for d in platform/executor mcp/plugins platform/estate; do
    [ -d "$SRC_ROOT/$d" ] || fail "missing source: $SRC_ROOT/$d"
  done
  ok "source: $SRC_ROOT"
}

# ---- detect python -------------------------------------------------------
detect_python() {
  hdr "python"
  local py=""
  for cand in \
    "$SRC_ROOT/sovereign/.venv/bin/python3" \
    /opt/homebrew/bin/python3.13 \
    /opt/homebrew/bin/python3.12 \
    /opt/homebrew/bin/python3.11 \
    /opt/homebrew/bin/python3.10 \
    /usr/local/bin/python3.13 \
    /usr/local/bin/python3.12 \
    /usr/local/bin/python3.11 \
    /usr/local/bin/python3.10 ; do
    [ -x "$cand" ] || continue
    local v=$("$cand" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null) || continue
    local maj=${v%.*} min=${v#*.}
    if [ "$maj" -ge 3 ] && [ "$min" -ge 10 ]; then
      py="$cand"; break
    fi
  done
  [ -n "$py" ] || fail "no python >= 3.10 found"
  ok "python: $py ($("$py" -V 2>&1))"
  PYTHON_BIN="$py"
}

# ---- detect harnesses ----------------------------------------------------
detect_harnesses() {
  hdr "harnesses"
  HARNESSES=()
  for h in pi claude cline opencode aider; do
    local path
    path=$(command -v "$h" 2>/dev/null || true)
    [ -n "$path" ] || continue
    HARNESSES+=("$h:$path")
    ok "$h → $path"
  done
  [ "${#HARNESSES[@]}" -gt 0 ] || warn "no harnesses found"
}

# ---- state dir -----------------------------------------------------------
populate_state() {
  hdr "populate $STATE_DIR"
  mkdir -p "$STATE_DIR/bin" "$STATE_DIR/intents" "$STATE_DIR/libexec"

  # Symlink from source — no copy, always current
  ln -sfn "$SRC_ROOT/platform/estate/intents" "$STATE_DIR/intents_link"
  ln -sfn "$SRC_ROOT/platform/estate/libexec" "$STATE_DIR/libexec_link"
  ln -sfn "$SRC_ROOT/platform/estate/bin"   "$STATE_DIR/bin_link"

  # CLI wrappers
  for b in estate-execute estate-tickets estate-break-glass; do
    [ -f "$SRC_ROOT/platform/estate/bin/$b" ] || continue
    cat > "$STATE_DIR/bin/$b" <<SHIM
#!/usr/bin/env bash
exec "$PYTHON_BIN" "$SRC_ROOT/platform/estate/bin/$b" "\$@"
SHIM
    chmod +x "$STATE_DIR/bin/$b"
  done

  # Daemon launcher
  mkdir -p "$BIN_DIR"
  cat > "$BIN_DIR/estate-daemon" <<SHIM
#!/usr/bin/env bash
exec "$PYTHON_BIN" "$SRC_ROOT/platform/executor/daemon.py"
SHIM
  chmod +x "$BIN_DIR/estate-daemon"

  ok "intents: $(ls "$SRC_ROOT/platform/estate/intents" 2>/dev/null | wc -l | tr -d ' ')"
  ok "libexec: $(ls "$SRC_ROOT/platform/estate/libexec" 2>/dev/null | wc -l | tr -d ' ')"
  ok "cli:     $(ls "$STATE_DIR/bin" 2>/dev/null | wc -l | tr -d ' ')"
}

# ---- service manager (macOS / Linux) -------------------------------------
write_service() {
  hdr "service manager ($(uname))"

  if [ "$(uname)" = "Darwin" ]; then
    mkdir -p "$PLIST_DIR"
    cat > "$PLIST_DIR/ai.estate.executor.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ai.estate.executor</string>
  <key>ProgramArguments</key><array>
    <string>$PYTHON_BIN</string>
    <string>$SRC_ROOT/platform/executor/daemon.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$STATE_DIR/executor.out.log</string>
  <key>StandardErrorPath</key><string>$STATE_DIR/executor.err.log</string>
  <key>EnvironmentVariables</key><dict>
    <key>PYTHONPATH</key><string>$SRC_ROOT/sovereign:$SRC_ROOT/mcp/plugins</string>
  </dict>
</dict></plist>
PLIST
    ok "launchd plist written"

  elif [ "$(uname)" = "Linux" ]; then
    mkdir -p "$SYSTEMD_DIR"
    cat > "$SYSTEMD_DIR/estate-executor.service" <<SERVICE
[Unit]
Description=Estate executor daemon
After=network.target

[Service]
Type=simple
ExecStart=$PYTHON_BIN $SRC_ROOT/platform/executor/daemon.py
Restart=always
RestartSec=5
Environment=PYTHONPATH=$SRC_ROOT/sovereign:$SRC_ROOT/mcp/plugins
StandardOutput=append:$STATE_DIR/executor.out.log
StandardError=append:$STATE_DIR/executor.err.log

[Install]
WantedBy=default.target
SERVICE
    ok "systemd unit written"
    ok "enable with: systemctl --user daemon-reload && systemctl --user enable --now estate-executor"
  fi
}

reload_unit() {
  if [ "$(uname)" = "Darwin" ]; then
    launchctl bootout "gui/$(id -u)/ai.estate.executor" 2>/dev/null || true
    sleep 1
    launchctl bootstrap "gui/$(id -u)" "$PLIST_DIR/ai.estate.executor.plist" 2>&1 || warn "bootstrap failed"
    sleep 3
    ok "launchd unit reloaded"
  elif [ "$(uname)" = "Linux" ]; then
    systemctl --user daemon-reload 2>&1 || warn "daemon-reload failed"
    systemctl --user enable --now estate-executor 2>&1 || warn "enable failed"
    ok "systemd unit reloaded"
  fi
}

# ---- self-test -----------------------------------------------------------
self_test() {
  hdr "self-test"
  local fails=0

  if [ -S "$STATE_DIR/executor.sock" ]; then ok "socket"; else warn "socket missing"; fails=$((fails+1)); fi
  if pgrep -f 'daemon.py' >/dev/null 2>&1; then ok "daemon running"; else warn "daemon not running"; fails=$((fails+1)); fi
  if "$STATE_DIR/bin/estate-execute" --list >/dev/null 2>&1; then ok "estate-execute works"; else warn "estate-execute failed"; fails=$((fails+1)); fi
  local n
  n=$(ls "$SRC_ROOT/platform/estate/intents" 2>/dev/null | wc -l | tr -d ' ')
  ok "intents: $n"
  if [ "$(uname)" = "Darwin" ] && launchctl print "gui/$(id -u)/ai.estate.executor" >/dev/null 2>&1; then ok "launchd loaded"
  elif [ "$(uname)" = "Linux" ] && systemctl --user is-active estate-executor >/dev/null 2>&1; then ok "systemd active"
  else warn "service not loaded"; fails=$((fails+1)); fi

  echo ""
  if [ "$fails" -eq 0 ]; then ok "self-test GREEN"; return 0
  else warn "self-test RED ($fails failure(s))"; return 1; fi
}

# ---- doctor --------------------------------------------------------------
doctor() {
  hdr "doctor"
  printf '%-20s %s\n' "source:" "$SRC_ROOT"
  printf '%-20s %s\n' "socket:" "$([ -S "$STATE_DIR/executor.sock" ] && echo present || echo MISSING)"
  printf '%-20s %s\n' "daemon pid:" "$(pgrep -f daemon.py | head -1 || echo none)"
  if [ "$(uname)" = "Darwin" ]; then
    printf '%-20s %s\n' "launchd:" "$(launchctl print "gui/$(id -u)/ai.estate.executor" 2>/dev/null | awk '/state =/ {print $3}' || echo '(not loaded)')"
  elif [ "$(uname)" = "Linux" ]; then
    printf '%-20s %s\n' "systemd:" "$(systemctl --user is-active estate-executor 2>/dev/null || echo 'inactive')"
  fi
  echo ""
  printf 'intents (%s):\n' "$(ls "$SRC_ROOT/platform/estate/intents" 2>/dev/null | wc -l | tr -d ' ')"
  ls "$SRC_ROOT/platform/estate/intents" 2>/dev/null | sed 's/^/  /'
  echo ""
  tail -10 "$STATE_DIR/executor.err.log" 2>/dev/null | sed 's/^/  /'
}

# ---- main ----------------------------------------------------------------
main() {
  preflight
  detect_python
  detect_harnesses

  case "$MODE" in
    doctor)
      doctor; exit 0 ;;
    uninstall)
      if [ "$(uname)" = "Darwin" ]; then
        launchctl bootout "gui/$(id -u)/ai.estate.executor" 2>/dev/null || true
        rm -f "$PLIST_DIR/ai.estate.executor.plist"
      elif [ "$(uname)" = "Linux" ]; then
        systemctl --user disable --now estate-executor 2>/dev/null || true
        rm -f "$SYSTEMD_DIR/estate-executor.service"
      fi
      pkill -f daemon.py 2>/dev/null || true
      ok "uninstalled"; warn "state preserved at $STATE_DIR"
      exit 0 ;;
    dryrun) ok "dry-run complete"; exit 0 ;;
    install)
      populate_state
      write_service
      reload_unit
      if ! self_test; then fail "self-test failed — check $LOG_FILE"; fi
      echo ""
      ok "estate $VERSION installed"
      ok "logs: $LOG_FILE"
      ;;
  esac
}

main "$@"

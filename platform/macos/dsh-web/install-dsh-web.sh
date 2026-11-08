#!/bin/bash
# Install/verify the ai.estate.dsh-web LaunchAgent and hand port 3080 over to it.
#
# Design notes (why this is safe to run in the foreground):
#   * The agent is booted OUT first, so nothing retries while we work.
#   * Exactly ONE bootstrap happens, after the port is already free. A single
#     failure therefore writes one diagnostic instead of looping.
#   * Every step is asserted; the script reports PASS/FAIL and exits nonzero on
#     any failure rather than claiming success.
#   * It cleans up after itself: stale startup diagnostics from the migration
#     window, and the superseded handoff.sh.
set -uo pipefail

LABEL="ai.estate.dsh-web"
WS="$HOME/Documents/deepseek-harness/default-workspace"
PLIST_SRC="$WS/ai.estate.dsh-web.plist"
PLIST_DST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOGDIR="$HOME/.dsh/logs"
URL="http://127.0.0.1:3080/"
DOMAIN="gui/$(id -u)"
NODE_BIN="/Users/roseonyema/.nvm/versions/node/v26.13.0/bin/node"
DSH_ENTRYPOINT="/Users/roseonyema/.local/opt/dsh-standalone/lib/node_modules/@deepseek-ai/dsh/lib/bin.js"
DSH_PACKAGE_ROOT="/Users/roseonyema/.local/opt/dsh-standalone/lib/node_modules/@deepseek-ai/dsh"
EXPECTED_DSH_VERSION="0.2.1-rc.5"
RELEASE_VERSION="0.2.1-rc.5+estate.2"
RELEASE_ID="dsh-web-2026.11.08.2"
RELEASE_DIR="$HOME/.estate/releases/dsh-web"
RELEASE_FILE="$RELEASE_DIR/current.json"
TEMP_ROOT="${DSH_TEMP_DIR:-$WS/.tmp-dsh-web}"
CATALOG_BIN="$HOME/.estate/bin/dsh-router-catalog"
LAUNCH_WRAPPER="$HOME/.estate/bin/dsh-web-launchd"
mkdir -p "$TEMP_ROOT"

PASS=0
FAIL=0
ok()  { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS + 1)); }
bad() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL + 1)); }
step() { printf '\n== %s ==\n' "$1"; }
die() { printf '\n\033[31mABORTED\033[0m: %s\n' "$1"; exit 1; }

listener_pid() { lsof -ti tcp:3080 -sTCP:LISTEN 2>/dev/null | head -1; }
bare_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$URL" 2>/dev/null; }

# The web surface is authenticated by design: the bare URL answers 401 until the
# browser holds the signed cookie that ONLY the launch-token URL can mint
# (dsh-client-connection: TOKEN_QUERY="token", authorizeIndex mints the cookie
# and redirects to ./). "200 on the bare URL" can therefore never pass, and
# asserting it reports a healthy service as broken. The contract is:
#   bare URL  -> 401 (auth gate up)
#   token URL -> 303 + Set-Cookie, then 200 serving index.html
JAR="$(mktemp "$TEMP_ROOT/dsh-auth-jar.XXXXXX")"
BODY="$(mktemp "$TEMP_ROOT/dsh-auth-body.XXXXXX")"
cleanup_temp() { rm -f "$JAR" "$BODY" "${RELEASE_TMP:-}" 2>/dev/null || true; }
trap cleanup_temp EXIT
launch_url() { grep -o 'http://127\.0\.0\.1:3080/?token=[A-Za-z0-9_-]*' "$LOGDIR/web.out.log" 2>/dev/null | tail -1; }
auth_code() { curl -s -L -c "$JAR" -b "$JAR" -o "$BODY" -w '%{http_code}' --max-time 20 "$1" 2>/dev/null; }

printf 'dsH web service install + handoff\n%s\n' "$(date)"

# ── 1. preflight ────────────────────────────────────────────────────────────
step "1. preflight"
[ -f "$PLIST_SRC" ] || die "source plist not found at $PLIST_SRC"
ok "source plist present"
[ -x "$NODE_BIN" ] || die "pinned node binary missing"
ok "pinned node binary exists"
[ -f "$DSH_ENTRYPOINT" ] || die "pinned standalone dsh entrypoint missing"
ok "pinned standalone dsh entrypoint exists"
[ -x "$CATALOG_BIN" ] || die "router catalogue synchronizer missing at $CATALOG_BIN"
ok "router catalogue synchronizer is executable"
[ -x "$LAUNCH_WRAPPER" ] || die "launch wrapper missing at $LAUNCH_WRAPPER"
ok "launch wrapper is executable"
INSTALLED_DSH_VERSION=$(
  "$NODE_BIN" -p "require(process.argv[1] + '/package.json').version" "$DSH_PACKAGE_ROOT"
) || die "could not read the installed dsh version"
[ "$INSTALLED_DSH_VERSION" = "$EXPECTED_DSH_VERSION" ] \
  || die "installed dsh is $INSTALLED_DSH_VERSION, expected $EXPECTED_DSH_VERSION"
ok "installed dsh version matches $EXPECTED_DSH_VERSION"
SOURCE_SHA="${DSH_SOURCE_SHA:-}"
printf '%s' "$SOURCE_SHA" | grep -Eq '^[0-9a-f]{40}$' \
  || die "DSH_SOURCE_SHA must be the exact 40-character source commit"
ok "source commit recorded as $SOURCE_SHA"
mkdir -p "$LOGDIR" && ok "log directory present"

if diff -q "$PLIST_SRC" "$PLIST_DST" >/dev/null 2>&1; then
  ok "installed plist matches source"
else
  cp "$PLIST_SRC" "$PLIST_DST" || die "could not install plist"
  ok "installed plist refreshed from source"
fi
plutil -lint "$PLIST_DST" >/dev/null 2>&1 && ok "installed plist is valid" || die "installed plist invalid"

# ── 2. quiesce: nothing may be retrying while we work ───────────────────────
step "2. quiesce the agent"
if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null
  for _ in $(seq 1 15); do
    launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 || break
    sleep 1  # sleep-ok: poll the launchd service-removal condition
  done
  launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1 \
    && die "agent still loaded after bootout" || ok "agent unloaded"
else
  ok "agent was not loaded"
fi
BEFORE_FILES=$(ls "$LOGDIR"/startup-*.log 2>/dev/null | wc -l | tr -d ' ')
BEFORE_BYTES=$(cat "$LOGDIR"/web.err.log 2>/dev/null | wc -c | tr -d ' ')
sleep 5  # sleep-ok: hold quiesced long enough to prove log writes stopped
AFTER_FILES=$(ls "$LOGDIR"/startup-*.log 2>/dev/null | wc -l | tr -d ' ')
AFTER_BYTES=$(cat "$LOGDIR"/web.err.log 2>/dev/null | wc -c | tr -d ' ')
if [ "$BEFORE_FILES" = "$AFTER_FILES" ] && [ "$BEFORE_BYTES" = "$AFTER_BYTES" ]; then
  ok "writes quiesced ($AFTER_FILES diag files, $AFTER_BYTES err bytes, stable over 5s)"
else
  bad "logs still growing while unloaded"
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
  printf '\n== DRY RUN: stopping before the destructive step ==\n'
  printf 'RESULT: %d passed, %d failed (preflight + quiesce only)\n' "$PASS" "$FAIL"
  exit 0
fi

# launchd appends to these files. Preserve the prior boot's evidence, then give
# the new process fresh logs so health checks cannot be poisoned by stale errors.
ARCHIVE_STAMP=$(date -u +%Y%m%dT%H%M%SZ)
for LOG_NAME in web.out.log web.err.log; do
  LOG_PATH="$LOGDIR/$LOG_NAME"
  if [ -s "$LOG_PATH" ]; then
    ARCHIVE_PATH="$LOGDIR/${LOG_NAME%.log}.$ARCHIVE_STAMP.log"
    mv "$LOG_PATH" "$ARCHIVE_PATH" || die "could not archive $LOG_PATH"
    ok "archived $LOG_NAME -> $(basename "$ARCHIVE_PATH")"
  fi
done

# ── 3. free the port ────────────────────────────────────────────────────────
step "3. free port 3080"
OLD_PID=$(listener_pid)
if [ -n "${OLD_PID:-}" ]; then
  printf '  ... old instance pid %s holds 3080; sending TERM\n' "$OLD_PID"
  kill -TERM "$OLD_PID" 2>/dev/null
  for _ in $(seq 1 12); do
    [ -z "$(listener_pid)" ] && break
    sleep 1  # sleep-ok: poll the port-release condition
  done
  if [ -n "$(listener_pid)" ]; then
    printf '  ... still listening after 12s; sending KILL\n'
    kill -KILL "$OLD_PID" 2>/dev/null
    sleep 3  # sleep-ok: bounded grace after forced termination
  fi
  [ -z "$(listener_pid)" ] && ok "port 3080 freed (was pid $OLD_PID)" || die "port 3080 still held after TERM+KILL"
else
  ok "port 3080 already free"
  OLD_PID=""
fi

# ── 4. single bootstrap attempt ─────────────────────────────────────────────
step "4. start the agent (one attempt)"
launchctl bootstrap "$DOMAIN" "$PLIST_DST" 2>&1 \
  && ok "bootstrap accepted" || die "launchctl bootstrap rejected the plist"

NEW_PID=""
# dsh's module graph is large and a cold profile mount can take ~90s on this
# machine. Wait for the service to be UP (port bound AND the launch URL
# printed), not for a bare-URL 200 that the auth contract forbids.
for _ in $(seq 1 90); do
  sleep 2  # sleep-ok: poll the single bootstrap health condition
  [ -n "$(listener_pid)" ] && [ -n "$(launch_url)" ] && break
done

# ── 5. verify ───────────────────────────────────────────────────────────────
step "5. verify"
NEW_PID=$(listener_pid)

BARE=$(bare_code)
[ "$BARE" = "401" ] && ok "bare $URL answers 401 (auth gate up, as designed)" \
  || bad "bare $URL answered '$BARE', expected 401"

LAUNCH=$(launch_url)
if [ -n "$LAUNCH" ]; then
  ok "launch-token URL printed by the service"
  TOKEN_CODE=$(auth_code "$LAUNCH")
  [ "$TOKEN_CODE" = "200" ] && ok "launch URL authenticates and serves 200" \
    || bad "launch URL answered '$TOKEN_CODE', expected 200"
  if grep -qi '<html' "$BODY" 2>/dev/null; then
    ok "authenticated response body is the app's HTML"
  else
    bad "authenticated response body is not HTML ($(wc -c <"$BODY" | tr -d ' ') bytes)"
  fi
else
  bad "no launch-token URL in $LOGDIR/web.out.log"
  TOKEN_CODE="none"
fi

COUNT=$(lsof -ti tcp:3080 -sTCP:LISTEN 2>/dev/null | wc -l | tr -d ' ')
[ "$COUNT" = "1" ] && ok "exactly one listener on 3080" || bad "$COUNT listeners on 3080 (expected 1)"

if [ -n "${NEW_PID:-}" ] && [ "$NEW_PID" != "${OLD_PID:-}" ]; then
  ok "serving pid changed: ${OLD_PID:-none} -> $NEW_PID"
elif [ -n "${OLD_PID:-}" ]; then
  bad "serving pid is still the old process ($OLD_PID)"
fi

if [ -n "${NEW_PID:-}" ]; then
  PPID_NEW=$(ps -o ppid= -p "$NEW_PID" 2>/dev/null | tr -d ' ')
  [ "$PPID_NEW" = "1" ] && ok "pid $NEW_PID is parented by launchd (ppid 1)" \
    || bad "pid $NEW_PID ppid is '$PPID_NEW', not 1 — not launchd-owned"
fi

STATE=$(launchctl print "$DOMAIN/$LABEL" 2>/dev/null | grep -E '^\s+state = ' | head -1 | awk '{print $3}')
[ "$STATE" = "running" ] && ok "launchd state = running" || bad "launchd state = '${STATE:-unknown}'"

RUNS=$(launchctl print "$DOMAIN/$LABEL" 2>/dev/null | grep -E '^\s+runs = ' | head -1 | awk '{print $3}')
[ "${RUNS:-0}" = "1" ] && ok "runs = 1 (no restart loop)" || bad "runs = $RUNS (expected 1 — restart loop)"

grep -q '127.0.0.1:3080' "$LOGDIR/web.out.log" 2>/dev/null \
  && ok "out log shows the served URL" || bad "out log has no URL line"

ERR_BYTES=$(cat "$LOGDIR/web.err.log" 2>/dev/null | wc -c | tr -d ' ')
[ "$ERR_BYTES" = "0" ] && ok "err log is empty" || bad "err log has $ERR_BYTES bytes"

# ── 6. cleanup ──────────────────────────────────────────────────────────────
step "6. cleanup"
STALE=$(ls "$LOGDIR"/startup-*.log 2>/dev/null | wc -l | tr -d ' ')
rm -f "$LOGDIR"/startup-*.log
ok "removed $STALE startup diagnostic file(s)"
if [ -f "$WS/handoff.sh" ]; then
  rm -f "$WS/handoff.sh"
  ok "removed superseded handoff.sh"
else
  ok "no superseded handoff.sh to remove"
fi
FILE_COUNT=$(ls -1 "$LOGDIR" | wc -l | tr -d ' ')
ok "log directory holds $FILE_COUNT file(s), $(du -sk "$LOGDIR" | awk '{print $1}') KB"

# ── 7. release identity ─────────────────────────────────────────────────────
step "7. record release identity"
mkdir -p "$RELEASE_DIR"
CONFIG_DIGEST=$(
  {
    printf '%s\n' "$EXPECTED_DSH_VERSION"
    printf '%s\n' "$RELEASE_VERSION"
    cat "$HOME/.dsh/profiles/web/package.json"
    cat "$HOME/.dsh/profiles/web/cordis.patch.yml"
  } | shasum -a 256 | awk '{print $1}'
)
RELEASE_TMP="$(mktemp "$TEMP_ROOT/dsh-release.XXXXXX")"
printf '%s\n' \
  '{' \
  '  "contractId": "estate.dsh-web",' \
  '  "schemaVersion": "1.0.0",' \
  '  "surface": "macos",' \
  '  "release": {' \
  "    \"id\": \"$RELEASE_ID\"," \
  "    \"version\": \"$RELEASE_VERSION\"," \
  "    \"sourceSha\": \"$SOURCE_SHA\"," \
  "    \"configDigest\": \"sha256:$CONFIG_DIGEST\"," \
  "    \"authority\": \"work-surface\"," \
  '    "router": "estate.model-router",' \
  "    \"installedAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" \
  '  }' \
  '}' >"$RELEASE_TMP"
"$NODE_BIN" - "$RELEASE_TMP" <<'JS'
const fs = require("node:fs");
const value = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
if (value.contractId !== "estate.dsh-web") throw new Error("wrong contractId");
if (value.release.id !== "dsh-web-2026.11.08.1") throw new Error("wrong release id");
if (value.release.version !== "0.2.1-rc.5+estate.2") throw new Error("wrong release version");
if (!/^sha256:[0-9a-f]{64}$/.test(value.release.configDigest)) {
  throw new Error("wrong config digest");
}
JS
mv "$RELEASE_TMP" "$RELEASE_FILE"
ok "release identity written to $RELEASE_FILE"

# ── summary ─────────────────────────────────────────────────────────────────
printf '\n────────────────────────────────────\n'
printf 'RESULT: %d passed, %d failed\n' "$PASS" "$FAIL"
if [ "$FAIL" -eq 0 ]; then
  printf '\033[32mAll checks passed.\033[0m\n'
  printf 'Open this ONCE to mint the browser cookie, then use http://127.0.0.1:3080/ normally:\n'
  printf '  %s\n' "$(launch_url)"
  rm -f "$JAR" "$BODY"
  exit 0
fi
rm -f "$JAR" "$BODY"
printf '\033[31mFailures present. Evidence in %s\033[0m\n' "$LOGDIR"
tail -25 "$LOGDIR/web.err.log" 2>/dev/null
exit 1

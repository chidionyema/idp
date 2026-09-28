#!/usr/bin/env bash
# scheduler-venv -- build the venv bin/scheduler-up runs from ($IDP/.venv), with dagster at the
# versions the cluster image pins, and prove the scheduler's definitions import from it.
#
# Measured 2026-09-27: the Mac scheduler exited 78 on every launchd tick. `$IDP/.venv/bin/python`
# answered "Not a directory": the checkout still held the `.venv` blob committed in e48c6919
# (content: its own absolute path), untracked since 65588127 but never removed, so
# `python3 -m venv .venv` cannot replace it. And nothing on the Mac installs dagster at all --
# bin/idp-install-all puts only check-jsonschema in .venv -- so all 37 `runs_on: mac` jobs had no
# daemon.
#
# Pins come from estate-scheduler.Dockerfile, not a second copy here: Mac and cluster run one
# dagster. A non-directory .venv is MOVED to .venv.stale-<utc>, never deleted. Default dry run.
#
# Exit: 0 ok, 1 refused, 3 built but the scheduler does not import from it (verify failed).
set -uo pipefail
export PATH="/opt/local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
APPLY="${1:-false}"
case "$APPLY" in True|true) APPLY=1;; *) APPLY=0;; esac
IDP="${IDP_REPO:-$HOME/Documents/code/idp}"
V="$IDP/.venv"
DOCKERFILE="$IDP/estate-scheduler.Dockerfile"

[ -f "$DOCKERFILE" ] || { echo "REFUSED no $DOCKERFILE to read the dagster pins from"; exit 1; }
PINS=$(grep -oE '(dagster[a-z-]*)==[0-9][0-9.]*' "$DOCKERFILE" | sort -u | tr '\n' ' ')
case "$PINS" in *dagster==*) ;; *) echo "REFUSED no dagster==<version> pin in $DOCKERFILE"; exit 1;; esac
# the scheduler module imports yaml and requests; idp-verify needs check-jsonschema from this venv
PKGS="$PINS pyyaml requests check-jsonschema"

PY="${SCHEDULER_VENV_PYTHON:-}"
if [ -z "$PY" ]; then
  for c in python3.12 python3.11; do command -v "$c" >/dev/null 2>&1 && { PY=$(command -v "$c"); break; }; done
fi
[ -n "$PY" ] || { echo "REFUSED no python3.12 or python3.11 on PATH (dagster ${PINS%% *} needs >=3.10)"; exit 1; }

verify() {
  [ -x "$V/bin/dagster-daemon" ] && [ -x "$V/bin/dagster-webserver" ] || {
    echo "  !! $V/bin has no dagster-daemon/dagster-webserver"; return 1; }
  "$V/bin/python" -c "import sys; sys.path.insert(0, '$IDP/scheduler'); from estate_scheduler.definitions import defs; print('  schedule.yml ok:', len(list(defs.jobs or [])), 'jobs')"
}

echo "pins (from $(basename "$DOCKERFILE")): $PINS"
echo "python: $PY"
if [ -d "$V" ] && [ ! -L "$V" ] && verify 2>/dev/null; then
  echo "ok $V already runs the scheduler: nothing to do"; exit 0
fi

stale=""
if { [ -e "$V" ] || [ -L "$V" ]; } && { [ ! -d "$V" ] || [ -L "$V" ]; }; then
  stale="$V.stale-$(date -u +%Y%m%dT%H%M%SZ)"
  echo "  $V is not a directory ($( [ -L "$V" ] && echo symlink || echo file)): $([ "$APPLY" = 1 ] && echo moving || echo would move) to $stale"
fi
if [ "$APPLY" = 0 ]; then
  echo "  would build $V and pip install: $PKGS"
  echo "dry run: apply=true to build"; exit 0
fi

free_m=$(( $(df -k "$IDP" | awk 'NR==2 {print $4}') / 1024 ))
[ "$free_m" -ge 1500 ] || { echo "REFUSED ${free_m}M free under $IDP; the venv needs ~1500M (run disk-cleanup)"; exit 1; }

if [ -n "$stale" ]; then
  mv "$V" "$stale" || { echo "REFUSED could not move $V aside"; exit 1; }
fi
"$PY" -m venv "$V" || { echo "  !! venv creation failed"; exit 3; }
# shellcheck disable=SC2086  # PKGS is a word list by construction
"$V/bin/pip" install -q --upgrade pip $PKGS || { echo "  !! pip install failed"; exit 3; }
verify || exit 3
echo "ok $V built; bin/scheduler-up can start dagster-daemon (launchd re-runs it every 600s)"

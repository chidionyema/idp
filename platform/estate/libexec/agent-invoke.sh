#!/bin/bash
# agent-invoke.sh -- wake an agent to resolve a failed critical function, with the structured data.
#
# WHY. 2026-10-28. The spine raises a structured incident and alerts; the estate's mandate is
# that the thing is then FIXED, not merely reported: "anything watching critical function that
# dies needs alert and auto invocation of agent, with structured data to resolve".
#
# TWO LANES, AND THE HONEST ONE IS USED.
#   1. THE SESSION DOOR (sb start) -- the estate's own fleet-scale work plane, with its budget,
#      its approval gates and its runner registry. It is tried FIRST, because it is the sanctioned
#      door and it is the only one that records the work in the estate's own ledger.
#   2. THE LOCAL LANE (claude -p) -- the founder's Claude Code subscription, run non-interactively
#      in the background with the incident attached. It is the fallback because the session door
#      is DOWN at the moment: sb start fails at sovereign/engine/client.py (Temporal unreachable),
#      and nothing listens on 127.0.0.1:16223.
#
# WHICH LANE WAS USED IS RECORDED, in the returned JSON and in the incident. A claim of "an agent
# was invoked" that does not say how is not a claim.
#
# USAGE
#   agent-invoke.sh --json '{"incident": {...}, "task": "...", "runner": "claude", "repo": "...", "budget": 20}'
#   agent-invoke.sh --task-file /tmp/task.json
#
# It prints ONE line of JSON on stdout: {"invoked": true, "invoked_via": "...", ...}.
set -uo pipefail

PAYLOAD=""
while [ $# -gt 0 ]; do
	case "$1" in
		--json) PAYLOAD="${2:-}"; shift 2 ;;
		--task-file) PAYLOAD="$(cat "${2:-}" 2>/dev/null)"; shift 2 ;;
		*) shift ;;
	esac
done
[ -n "$PAYLOAD" ] || { echo '{"invoked": false, "error": "no payload"}'; exit 2; }

# One field at a time, through json: the incident is a multi-line object and a positional
# `read` would take its first line and lose the rest of the evidence.
jget() {
	printf '%s' "$PAYLOAD" | /usr/bin/python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
v = d.get(sys.argv[1], "")
print(v if isinstance(v, str) else json.dumps(v))
' "$1" 2>/dev/null
}
TASK=$(jget task)
RUNNER=$(jget runner)
REPO=$(jget repo)
BUDGET=$(jget budget)
INCIDENT=$(jget incident)
[ -n "$TASK" ] || { echo '{"invoked": false, "error": "the payload has no task"}'; exit 2; }

TEMPORAL="${CRITICAL_WATCH_TEMPORAL:-127.0.0.1:16223}"
LOGDIR="$HOME/.estate/incidents"
mkdir -p "$LOGDIR"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
LOG="$LOGDIR/agent-$STAMP.log"

# --- lane 1: the estate's own session door ---------------------------------
temporal_open() {
	/usr/bin/python3 - "$TEMPORAL" <<'PY'
import socket, sys
host, _, port = sys.argv[1].partition(":")
s = socket.socket(); s.settimeout(2)
try:
    s.connect((host, int(port)))
except OSError:
    sys.exit(1)
finally:
    s.close()
sys.exit(0)
PY
}

if temporal_open; then
	SB="${ESTATE_SB:-$HOME/Documents/code/idp/bin/sb}"
	[ -x "$SB" ] || SB="$(command -v sb 2>/dev/null)"
	if [ -n "$SB" ] && [ -x "$SB" ]; then
		OUT=$(cd "$REPO" 2>/dev/null && timeout 90 "$SB" start --task "$TASK" --runner "$RUNNER" --budget "$BUDGET" --json 2>&1)
		RC=$?
		if [ "$RC" = 0 ]; then
			printf '{"invoked": true, "invoked_via": "session", "rc": 0, "log": "%s", "output": %s}\n' \
				"$LOG" "$(printf '%s' "$OUT" | /usr/bin/python3 -c 'import json,sys
try:
    print(json.dumps(sys.stdin.read()))
except Exception:
    print("\"\"")' 2>/dev/null)"
			exit 0
		fi
		printf '%s\n' "$OUT" >"$LOG.session-failed"
	fi
fi

# --- lane 2: the local claude lane ----------------------------------------
CLAUDE="${ESTATE_CLAUDE:-$HOME/.local/bin/claude}"
[ -x "$CLAUDE" ] || CLAUDE="$(command -v claude 2>/dev/null)"
if [ -z "$CLAUDE" ] || [ ! -x "$CLAUDE" ]; then
	printf '{"invoked": false, "invoked_via": "none", "error": "no session door (Temporal unreachable) and no local claude lane"}\n'
	exit 3
fi

PROMPT="$TASK

Here is the structured incident record. Resolve it with what is in here, measure the result, and
report what you measured (not what you intended). Do not touch another agent's worktrees, claims
or scratch, and do not hand-apply infrastructure.

$INCIDENT"

(
	cd "$REPO" 2>/dev/null || cd "$HOME" || exit 1
	"$CLAUDE" -p "$PROMPT" --permission-mode acceptEdits >"$LOG" 2>&1
	echo "exit=$?" >>"$LOG"
) &
PID=$!
printf '{"invoked": true, "invoked_via": "local-claude", "pid": %s, "log": "%s", "note": "the estate session door was unreachable (Temporal); the local claude lane was used instead"}\n' \
	"$PID" "$LOG"
exit 0

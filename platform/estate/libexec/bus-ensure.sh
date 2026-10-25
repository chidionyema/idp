#!/usr/bin/env bash
# Is the estate bus beside the door actually answering, and if not, put it back?
#
# The probe is the protocol, not the process: a broker that accepted a socket and never sent its
# INFO line is exactly the failure that cost this machine a day (launchd reported the job healthy
# while nothing bound), so `pgrep nats-server` is not evidence and is not used as one.
#
# The tap is ensured too, and for the same reason: publishing to a broker that nothing reads is
# only half a plane. `bin/estate-friction-tap` appends what the bus carries into the ledger that
# /fleet and pi-observe already read, and is restarted here when it is not there.
#
# Exit: 0 answering (already or after a restart), 1 still silent, 2 cannot even try (no binary).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ESTATE_NATS_PORT:-4222}"
TAP="${ESTATE_FRICTION_TAP:-$HERE/../bin/estate-friction-tap}"  # ~/.estate/libexec -> ~/.estate/bin
TAP_TICKLE="${ESTATE_FRICTION_TAP_TICKLE:-$HOME/.estate/friction-tap.log}"

probe() {
  python3 - "$PORT" <<'PY'
import socket, sys
port = int(sys.argv[1])
try:
    s = socket.create_connection(("127.0.0.1", port), timeout=2)
except OSError as exc:
    print(f"silent: {exc}")
    raise SystemExit(1)
s.settimeout(2)
try:
    line = s.recv(256)
finally:
    s.close()
if line.startswith(b"INFO "):
    print("answering")
    raise SystemExit(0)
print("silent: accepted the connection and said nothing")
raise SystemExit(1)
PY
}

ensure_tap() {
  # The tap is alive when its pid exists and is still running; a wedged tap is indistinguishable from
  # a quiet one otherwise, and a quiet bus is a normal state.
  local pidfile="$HOME/.estate/friction-tap.pid"
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile" 2>/dev/null)" 2>/dev/null; then
    echo "friction tap: running (pid $(cat "$pidfile"))"
    return 0
  fi
  # A tap started before its pidfile was written is still a tap: never start a second one beside it.
  if pgrep -f 'estate-friction-tap' >/dev/null 2>&1; then
    echo "friction tap: running (pid $(pgrep -f 'estate-friction-tap' | head -1))"
    return 0
  fi
  if [ ! -f "$TAP" ]; then
    echo "friction tap: not started, $TAP is missing" >&2
    return 0
  fi
  python3 "$TAP" >/dev/null 2>&1 &
  # Measured 2026-10-24: 0.3s was too short -- the tap was already running and this still printed
  # "did not start", so the check lied about a healthy plane. Wait up to 2s, then ask pgrep too.
  for _ in 1 2 3 4; do
    if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile" 2>/dev/null)" 2>/dev/null; then
      echo "friction tap: started (pid $(cat "$pidfile"))"
      return 0
    fi
    python3 -c 'import time; time.sleep(0.5)'
  done
  if pid=$(pgrep -f 'estate-friction-tap' | head -1) && [ -n "$pid" ]; then
    echo "friction tap: started (pid $pid, pidfile not yet written)"
  else
    echo "friction tap: did not start; see $TAP_TICKLE" >&2
  fi
}

if out="$(probe)"; then
  echo "bus ${PORT}: $out (no action)"
  ensure_tap
  exit 0
fi

echo "bus ${PORT}: $out -- starting it detached"
python3 "$HERE/bus-start.py" || exit 2

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if out="$(probe)"; then
    echo "bus ${PORT}: $out after restart"
    ensure_tap
    exit 0
  fi
  python3 -c 'import time; time.sleep(0.5)'
done

echo "bus ${PORT}: still $out after a restart attempt -- the store may need attention" >&2
echo "  next: tail -20 \"\${HOME}/.estate/nats.out.log\"" >&2
exit 1

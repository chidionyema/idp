#!/usr/bin/env bash
# Is the estate bus beside the door actually answering, and if not, put it back?
#
# The probe is the protocol, not the process: a broker that accepted a socket and never sent its
# INFO line is exactly the failure that cost this machine a day (launchd reported the job healthy
# while nothing bound), so `pgrep nats-server` is not evidence and is not used as one.
#
# Exit: 0 answering (already or after a restart), 1 still silent, 2 cannot even try (no binary).
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${ESTATE_NATS_PORT:-4222}"

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

if out="$(probe)"; then
  echo "bus ${PORT}: $out (no action)"
  exit 0
fi

echo "bus ${PORT}: $out -- starting it detached"
python3 "$HERE/bus-start.py" || exit 2

for _ in 1 2 3 4 5 6 7 8 9 10; do
  if out="$(probe)"; then
    echo "bus ${PORT}: $out after restart"
    exit 0
  fi
  python3 -c 'import time; time.sleep(0.5)'
done

echo "bus ${PORT}: still $out after a restart attempt -- the store may need attention" >&2
echo "  next: tail -20 \"\${HOME}/.estate/nats.out.log\"" >&2
exit 1

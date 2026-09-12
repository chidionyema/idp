"""Publish every router lane change onto the estate bus, the moment Postgres commits it.

WHY A LISTENER AND NOT A POLL. A poll every N seconds means the estate believes something for up
to N seconds after it stopped being true, and the width of that window is the size of the lie.
Founder, 2026-09-12: "we eliminate the 5-minute polling script entirely. We rely on physics."

THE PAYLOAD CARRIES NO SECRET. pg_notify is visible to every session on the database, so the
trigger sends `op`, `table`, `model` and a timestamp -- where to look, never what is there. This
publishes that same shape and adds the source.

WHY THE WIRE PROTOCOL BY HAND. One PUB to one subject does not justify a client library in an
image built to be small; the estate's other publishers open a socket the same way.
"""

from __future__ import annotations

import json
import os
import pathlib
import select
import socket
import sys
import time

import psycopg

DSN = (
    "host=estate-rw.estate-db.svc.cluster.local port=5432 user=litellm dbname=litellm password="
    + open(os.environ["PGPASSWORD_FILE"]).read().strip()
)
NATS_URL = os.environ["NATS_URL"]
SUBJECT = "estate.ai.router.changed"


# /tmp here is the pod's OWN emptyDir (publisher.yaml declares the volume), not a shared system
# temporary directory, so there is nothing to race with and nothing to leak between workloads.
# ruff's S108 cannot see a volume declaration; the exemption is stated rather than silenced.
HEARTBEAT = "/tmp/subscribed"  # noqa: S108


def log(msg: object) -> None:
    print(
        json.dumps(
            {"msg": msg, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        ),
        flush=True,
    )


def publish(payload: dict) -> None:
    """One PUB to JetStream, and wait for the PONG so 'sent' is never claimed before the bus took it."""
    host, port = NATS_URL.rsplit(":", 1)
    with socket.create_connection((host, int(port)), timeout=10) as s:
        s.sendall(b'CONNECT {"verbose":false,"pedantic":false}\r\n')
        body = json.dumps(payload).encode()
        s.sendall(f"PUB {SUBJECT} {len(body)}\r\n".encode() + body + b"\r\n")
        s.sendall(b"PING\r\n")
        s.settimeout(5)
        try:
            s.recv(64)
        except socket.timeout as exc:
            raise RuntimeError(
                "bus did not acknowledge; the event was not delivered"
            ) from exc


def main() -> int:
    log(f"listening on {DSN.split('user=')[-1]}")
    while True:
        try:
            conn = psycopg.connect(DSN)
            conn.set_isolation_level(psycopg.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            with conn.cursor() as cur:
                cur.execute("LISTEN estate_router_changed;")
            log("subscribed to estate_router_changed")
            # The readiness signal the probes read. Written only once the LISTEN is genuinely live,
            # and refreshed on every poll, so a pod that has lost its connection stops being Ready
            # rather than sitting there looking healthy while the feed is dark.
            pathlib.Path(HEARTBEAT).touch()
            while True:
                pathlib.Path(HEARTBEAT).touch()
                if not select.select([conn], [], [], 30)[0]:
                    # A quiet bus is not a dead one. This keeps the connection warm and turns a
                    # broken socket into a reconnect rather than a hang.
                    conn.poll()
                    continue
                conn.poll()
                while conn.notifies:
                    n = conn.notifies.pop(0)
                    try:
                        event = json.loads(n.payload)
                    except ValueError:
                        log(f"unparseable payload, dropped: {n.payload[:80]}")
                        continue
                    event["source"] = "estate-db"
                    publish(event)
                    log(f"published {event.get('op')} {event.get('model')}")
        except Exception as exc:  # noqa: BLE001 -- a database that went away must not end the feed
            pathlib.Path(HEARTBEAT).unlink(missing_ok=True)
            log(f"reconnecting after: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    sys.exit(main())

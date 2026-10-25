#!/usr/bin/env python3
"""Start the estate bus detached from whatever job asked for it.

WHY THIS EXISTS SEPARATELY FROM launchd. Measured 2026-10-24: the launchd job for the laptop's
broker sat at `state = running` with a live pid and no listener -- twice -- while a detached start
of the same binary, same arguments, same store greeted a client in under a second. A supervisor
that reports healthy while the service binds nothing is worse than no supervisor, so the bus is
ensured by something that measures the service instead of trusting the supervisor: bus-ensure.sh
probes the protocol, and this script does the starting when the probe says nothing is there.

macOS has no setsid(1); the double fork plus setsid(2) is the portable way to leave a process that
no shell, no job and no launchd job can kill by reaping its process group.
"""

import os
import pathlib
import sys
import time

HOME = pathlib.Path.home()
BIN = pathlib.Path(
    os.environ.get("ESTATE_NATS_BIN", HOME / ".cache/estate-tools/nats-server")
)
STORE = pathlib.Path(os.environ.get("ESTATE_NATS_STORE", HOME / ".estate/nats"))
PORT = os.environ.get("ESTATE_NATS_PORT", "4222")
HTTP_PORT = os.environ.get("ESTATE_NATS_HTTP_PORT", "8222")
PIDFILE = pathlib.Path(os.environ.get("ESTATE_NATS_PIDFILE", HOME / ".estate/nats.pid"))
OUT = pathlib.Path(os.environ.get("ESTATE_NATS_LOG", HOME / ".estate/nats.out.log"))


def main() -> int:
    if not BIN.exists():
        print(f"BLIND bus-start: no broker binary at {BIN}")
        return 2
    STORE.mkdir(parents=True, exist_ok=True)
    if os.fork() > 0:
        time.sleep(
            0.6
        )  # let the child write the pidfile and exec before the caller re-probes
        return 0
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    os.dup2(os.open(os.devnull, os.O_RDONLY), 0)
    log = os.open(OUT, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    os.dup2(log, 1)
    os.dup2(log, 2)
    PIDFILE.write_text(str(os.getpid()))
    os.execv(  # noqa: S606 -- becomes the broker binary in place, keeping the pid it was given
        str(BIN),
        [
            str(BIN),
            "--jetstream",
            "--store_dir",
            str(STORE),
            "--addr",
            "127.0.0.1",
            "--port",
            PORT,
            "--http_port",
            HTTP_PORT,
        ],
    )
    os._exit(127)


if __name__ == "__main__":
    sys.exit(main())

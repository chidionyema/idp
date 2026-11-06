"""Forward estate work out of a read-only agent sandbox to the host executor.

The Codex desktop runs shell commands inside a Seatbelt sandbox.  The estate's ticket database
lives under ``~/.estate`` and is writable by the user, but not from inside that sandbox, so a
direct ``estate-execute`` reaches SQLite's misleading "attempt to write a readonly database"
error before an intent starts.  This module bridges the one supported host boundary: the
same authenticated ``executor.sock`` used by estate intents.

The bridge is deliberately not a fallback that keeps running locally after a failed write.
That would lose the audit ticket and could execute host-owned intents with the wrong filesystem
view.  It either forwards the exact argv with the current session identity or fails clearly.
"""

from __future__ import annotations

import json
import os
import shlex
import socket
import stat
import sys
import time
from os import environ
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

BRIDGE_CHILD = "ESTATE_HOST_EXECUTE"
SANDBOX_MARKER = "CODEX_SANDBOX"
SANDBOX_VALUE = "seatbelt"
DEFAULT_SOCKET = Path.home() / ".estate" / "executor.sock"
DEFAULT_CEILING_S = 120


def _session(env: Mapping[str, str]) -> str:
    return (
        env.get("ESTATE_SESSION_ID", "").strip()
        or env.get("CODEX_SESSION_ID", "").strip()
    )


def should_forward(
    env: Optional[Mapping[str, str]] = None,
    socket_path: Optional[Path] = None,
) -> bool:
    """Whether this invocation is sandboxed and has a live host door to cross."""
    e = env if env is not None else environ
    if e.get(SANDBOX_MARKER, "").strip().lower() != SANDBOX_VALUE:
        return False
    if e.get(BRIDGE_CHILD, "") == "1":
        return False
    try:
        mode = Path(socket_path or e.get("IDP_EXECUTOR_SOCKET") or DEFAULT_SOCKET).stat().st_mode
    except OSError:
        return False
    return stat.S_ISSOCK(mode)


def forwarded_command(
    executable: Path,
    argv: Sequence[str],
    session_id: str,
) -> str:
    """Build one shell-safe command for the host-side estate-execute process."""
    if not session_id.strip():
        raise ValueError(
            "the sandbox bridge requires ESTATE_SESSION_ID or CODEX_SESSION_ID; "
            "forwarding without identity would turn the plan gate into automation"
        )
    prefix = [
        "env",
        BRIDGE_CHILD + "=1",
    ]
    prefix.extend(
        [
            str(executable),
            *argv,
            "--session",
            session_id,
        ]
    )
    return " ".join(shlex.quote(part) for part in prefix)


def _call(payload: dict, socket_path: Path, timeout: float) -> dict:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect(str(socket_path))
        sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")
        raw = b""
        while b"\n" not in raw:
            chunk = sock.recv(65536)
            if not chunk:
                break
            raw += chunk
    finally:
        sock.close()
    if not raw:
        raise OSError("the host executor closed without a reply")
    reply = json.loads(raw.decode("utf-8").splitlines()[0])
    if not isinstance(reply, dict):
        raise OSError("the host executor returned a non-object reply")
    return reply


def forward(
    executable: Path,
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Optional[Mapping[str, str]] = None,
    socket_path: Optional[Path] = None,
    ceiling_sec: int = DEFAULT_CEILING_S,
    call: Callable[[dict, Path, float], dict] = _call,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    stdout=sys.stdout,
    stderr=sys.stderr,
) -> Optional[int]:
    """Run this same command on the host and relay its final state.

    ``None`` means this process is not sandboxed (or is already the forwarded child), so the
    caller should continue normally.  An integer is the exit status to return.
    """
    e = env if env is not None else environ
    door = Path(socket_path or e.get("IDP_EXECUTOR_SOCKET") or DEFAULT_SOCKET)
    if not should_forward(e, door):
        return None

    session_id = _session(e)
    try:
        command = forwarded_command(executable, argv, session_id)
    except ValueError as exc:
        print(f"estate-execute: {exc}", file=stderr)
        return 2

    accepted = call(
        {
            "verb": "execute",
            "command": command,
            "cwd": str(cwd),
            "ceiling_sec": ceiling_sec,
            "session_id": session_id,
        },
        door,
        10.0,
    )
    if not accepted.get("ok"):
        print(
            "estate-execute: host execution refused: "
            + str(accepted.get("error") or accepted.get("reason") or "unknown refusal"),
            file=stderr,
        )
        return 3

    job_id = str(accepted.get("job_id") or "")
    if not job_id:
        print("estate-execute: host executor accepted no job id", file=stderr)
        return 3

    deadline = clock() + ceiling_sec + 5
    while clock() < deadline:
        reply = call({"verb": "read", "job_id": job_id}, door, 5.0)
        result = reply.get("result") if reply.get("ok") else None
        if not isinstance(result, dict):
            print("estate-execute: host executor returned an unreadable job", file=stderr)
            return 3
        if not result.get("found"):
            print(f"estate-execute: host executor lost job {job_id}", file=stderr)
            return 3
        if result.get("state") != "accepted":
            log = str(result.get("log") or "")
            if log:
                print(log, end="" if log.endswith("\n") else "\n", file=stdout)
            return int(result.get("exit_code") or 0)
        sleep(0.2)

    print(
        f"estate-execute: host job {job_id} exceeded the {ceiling_sec}s bridge budget",
        file=stderr,
    )
    return 124

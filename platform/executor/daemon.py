"""The executor daemon: the process that runs commands, so the agent's process tree does not.

ORDER (founder, 2026-09-13, verbatim):
    "If you want ultra-high-tech governance, the agent shouldn't have raw, unrestricted bash
     spawned directly from its own process tree anyway. It should request execution from an
     isolated daemon."
    "we should alreay habe this , we alreadfy solbve thing nbut nnothing gets opertionnal"

WHAT THIS IS, and what it deliberately is not:
  It is the thin transport between the agent and the detached runner this estate ALREADY built
  and proved -- `~/.pi/agent/bin/run`, which starts a command with nohup in its own session,
  writes `~/.estate/runs/<id>.log`, records the pid, and returns in milliseconds. Nothing here
  re-implements that (LAW 43: never reinvent a wheel a mature tool already does).

  What this file adds is the part that was missing: the ceiling is applied HERE, on the far side
  of a message, by a process the agent's tool calls do not live inside. A caller that forgets the
  ceiling, or rewrites itself, does not remove it.

THE HONEST LIMIT, stated because a claim the file cannot support is the defect this estate keeps
repeating: running under launchd does NOT by itself stop the agent from editing this file. It runs
as the same uid. What makes the boundary real is the ownership step in `bin/idp-executor-install`
(a separate uid owning the plist and the runner), and this daemon is the half that can be built
today. `bin/idp-executor-status` reports which half is actually in place, so nobody reads a
half-boundary as a whole one.

Transport: a UNIX domain socket, not a TCP port. A port would be a network surface on a laptop
(LAW 21: secure by default); a socket is a file, and its permissions are the access control.
"""

from __future__ import annotations

import json
import os
import socket
import socketserver
import stat
import sys

# Import the door's own logic rather than restating it. One ceiling, one parser, one answer --
# a second copy of the check is a second answer, and they drift.
#
# This import is FAIL-CLOSED, and it was measured 2026-09-13: the first version caught
# ImportError and quietly set CEILING_SEC = 60, so the daemon came up, answered `health` with
# `ok: true`, and then raised `NameError: execute_command is not defined` on every execute.
# A health check that passes while the door cannot run anything is exactly the lie this estate
# keeps catching. No fallback: if the door cannot be imported, the daemon refuses to start.
_PLUGINS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "mcp", "plugins"
)
sys.path.insert(0, os.path.abspath(_PLUGINS))
from estate_executor import (  # noqa: E402
    CEILING_SEC,
    execute_command,
    read_job,
    simulate_command,
)

# The socket lives under the estate's own state directory, never /tmp: a world-writable directory
# lets another local user replace the socket and receive the agent's commands (LAW 21).
SOCKET_PATH = os.environ.get(
    "IDP_EXECUTOR_SOCKET", os.path.expanduser("~/.estate/executor.sock")
)

# The ceiling is enforced with the platform's own bound, not by asking politely. `timeout` is the
# mature tool for this and it is already on PATH (measured: /usr/local/bin/timeout).
TIMEOUT_BIN = os.environ.get("IDP_TIMEOUT_BIN", "/usr/local/bin/timeout")


def _runner_argv(
    job_id: str, command: str, cwd: str | None, ceiling_sec: int
) -> list[str]:
    """The argv that starts the work detached, bounded by the ceiling.

    `timeout` wraps the command so the bound is enforced by the kernel, not by this loop watching a
    clock (LAW 43). `run` starts it detached so this daemon is never the thing holding a turn open.
    """
    inner = [TIMEOUT_BIN, "--signal=TERM", f"{ceiling_sec}s", "bash", "-lc", command]
    argv = [os.path.expanduser("~/.pi/agent/bin/run"), job_id, *inner]
    if cwd:
        argv = [os.path.expanduser("~/.pi/agent/bin/run"), "--cwd", cwd, job_id, *inner]
    return argv


class Handler(socketserver.StreamRequestHandler):
    """One request, one answer, no state held between them.

    The replies are small JSON objects and always arrive in milliseconds: the daemon starts work
    and answers. It never waits for the command, because a daemon that waits is the blocking call
    it was built to remove (LAW 55).
    """

    def handle(
        self,
    ) -> None:  # pragma: no cover - exercised by bin/idp-executor-status --prove
        try:
            raw = self.rfile.readline(1_000_000)
            if not raw:
                return
            request = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            self._reply({"ok": False, "error": f"malformed request: {exc}"})
            return

        verb = request.get("verb")
        if verb == "execute":
            self._reply(self._execute(request))
        elif verb == "simulate":
            self._reply(
                {
                    "ok": True,
                    "result": simulate_command(
                        request.get("command", ""),
                        cwd=request.get("cwd"),
                        ceiling_sec=request.get("ceiling_sec", CEILING_SEC),
                    ),
                }
            )
        elif verb == "read":
            self._reply({"ok": True, "result": read_job(request.get("job_id", ""))})
        elif verb == "health":
            self._reply(
                {
                    "ok": True,
                    "ceiling_sec": CEILING_SEC,
                    "pid": os.getpid(),
                    "timeout_bin": TIMEOUT_BIN,
                    "timeout_present": os.path.exists(TIMEOUT_BIN),
                }
            )
        else:
            # An unknown verb is REFUSED, never ignored: a door that silently does something else
            # is worse than one that says no (the `--help` defect, measured 2026-09-13).
            self._reply({"ok": False, "error": f"unknown verb {verb!r}"})

    def _execute(self, request: dict) -> dict:
        import subprocess  # local: kept out of the pure import path used by the tests

        # The door decides. This handler does not re-check the ceiling -- one check, one answer.
        verdict = execute_command(
            request.get("command", ""),
            cwd=request.get("cwd"),
            ceiling_sec=request.get("ceiling_sec", CEILING_SEC),
        )
        if not verdict.get("accepted"):
            return {"ok": False, "refused": True, "error": verdict.get("error")}

        job_id = verdict["job_id"]
        argv = _runner_argv(
            job_id, request["command"], request.get("cwd"), verdict["ceiling_sec"]
        )
        try:
            subprocess.Popen(
                argv,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            return {
                "ok": False,
                "error": f"the detached runner could not be started: {exc}",
            }
        return {"ok": True, "job_id": job_id, "ceiling_sec": verdict["ceiling_sec"]}

    def _reply(self, payload: dict) -> None:
        self.wfile.write((json.dumps(payload) + "\n").encode("utf-8"))


class Server(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True
    allow_reuse_address = False  # a stale socket must be an error, not silently stolen


def serve() -> None:  # pragma: no cover - the daemon loop
    os.makedirs(os.path.dirname(SOCKET_PATH), mode=0o700, exist_ok=True)
    if os.path.exists(SOCKET_PATH):
        # A socket that answers is a second daemon; one that does not is a leftover. Distinguish
        # rather than delete blindly, because deleting a live socket is an outage (R38).
        if _answers(SOCKET_PATH):
            print(
                f"refused: another executor is already answering on {SOCKET_PATH}",
                file=sys.stderr,
            )
            raise SystemExit(2)
        os.unlink(SOCKET_PATH)

    server = Server(SOCKET_PATH, Handler)
    # Owner-only. The agent runs as the same uid today, so this is not the boundary yet -- it is
    # what makes the separate-uid step a one-line change rather than a rewrite.
    os.chmod(SOCKET_PATH, stat.S_IRUSR | stat.S_IWUSR)
    print(
        f"executor listening on {SOCKET_PATH} (ceiling {CEILING_SEC}s)", file=sys.stderr
    )
    server.serve_forever()


def _answers(path: str, timeout: float = 1.0) -> bool:
    """Does something actually answer on this socket?"""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        try:
            sock.connect(path)
            sock.sendall(b'{"verb":"health"}\n')
            return bool(sock.recv(4096))
        except OSError:
            return False


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        # A cheap, honest answer a person or a script can read.
        import shutil

        print(
            json.dumps(
                {
                    "socket": SOCKET_PATH,
                    "socket_exists": os.path.exists(SOCKET_PATH),
                    "answering": _answers(SOCKET_PATH)
                    if os.path.exists(SOCKET_PATH)
                    else False,
                    "ceiling_sec": CEILING_SEC,
                    "timeout_bin": TIMEOUT_BIN,
                    "timeout_present": bool(
                        shutil.which(TIMEOUT_BIN) or os.path.exists(TIMEOUT_BIN)
                    ),
                },
                indent=2,
            )
        )
        return 0
    serve()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

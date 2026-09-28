#!/usr/bin/env python3
"""run -- start a long command, return in milliseconds, read its output later.

THE PROBLEM THIS SOLVES, measured 2026-09-12. pi's bash tool runs a command in the FOREGROUND: the
agent's turn cannot end until the process exits. So a session that runs

    timeout 900 pytest tests/ -q

is unavailable for up to fifteen minutes -- no reply, no output, nothing. The person watching sees a
hung agent. I fixed `sleep` first and it was the wrong layer: the same block happens to `pytest`,
`gh run watch`, `kubectl wait`, and `curl --retry`, none of which sleep.

    run <name> <command...>
    run --cwd <dir> <name> <command...>

starts the command detached, writes stdout+stderr to <runs>/<name>.log, records the pid, and RETURNS
IMMEDIATELY. The turn ends; the work keeps going.

    run --status [<name>]     what is running, finished, or failed
    run --log <name>          tail its output
    run --wait <name> [secs]  block until it finishes -- only when you genuinely must

WHY THIS FILE IS PYTHON, NOT SHELL (2026-09-13). The shell version was 106 lines and the estate's own
guard refused it at commit: "new shell file is 106 lines, over 100: write it in Python (standard row
6, crew#620)". The guard was right, and not only on line count. In shell the command had to survive
`nohup "$@"` word-splitting, which is exactly how two real defects shipped: `--cwd` was read as the
job NAME (the only trace on disk was a file called `--cwd.pid`), and a single-string command was
looked up as a literal filename ("nohup: pwd && git rev-parse: No such file or directory"). Python's
argv is a list; there is nothing to split and nothing to quote. The defect class is gone, not fixed.

WHY THE CHILD SURVIVES THIS PROCESS: `start_new_session=True`. A background job in a shell dies when
that shell exits, which is immediately. A new session is what makes it outlive the call.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

RUNS = Path(os.environ.get("ESTATE_RUNS") or os.path.expanduser("~/.estate/runs"))

USAGE = (
    "run <name> <command...> | run --status [name] | run --log <name> | "
    "run --wait <name> [secs] | run --cwd <dir> <name> <command...>"
)

# The watcher RECORDS THE CHILD'S REAL EXIT CODE, and the only way to do that is to BE ITS PARENT.
#
# Measured 2026-09-13, and it cost a wrong answer in the log before it was found: a detached watcher
# that merely polls `kill -0 $pid` and then calls `wait $pid` records 127, not the command's code.
# `wait` in /bin/sh only waits on children OF THAT SHELL, and the watcher is not the child's parent,
# so `wait` fails -- and `$?` then captures the failure of `wait` itself. Every successful job would
# have been reported as "exited 127". That is the same class of lie as the bare '124' this file
# already carries a note about: a number a reader trusts, printed about something else entirely.
#
# So the shell does not watch the command, it RUNS it: `/bin/sh -c '<cmd>' sh <name> <args...>`,
# with the exit file handed over in the environment. The pid recorded below is the SHELL's, which is
# the handle that matters -- killing it is what stops the job. `exec` is deliberately not used: it
# would replace the shell and take the exit code with it.
_WRAPPER = 'a="$1"; shift; "$a" "$@"; rc=$?; echo $rc > "$EXIT_FILE"; exit $rc'


def _paths(name: str) -> tuple[Path, Path, Path]:
    return RUNS / f"{name}.log", RUNS / f"{name}.pid", RUNS / f"{name}.exit"


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _tail_text(path: Path, n: int) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(errors="replace").splitlines()[-n:])


def status(one: str | None) -> int:
    if one:
        log, pidf, _ = _paths(one)
        pid = pidf.read_text().strip() if pidf.exists() else "-"
        print(f"pidfile {pid}  log {log}")
        print(_tail_text(log, 5))
        return 0
    if not RUNS.exists():
        print("nothing has been run")
        return 0
    for pidf in sorted(RUNS.glob("*.pid")):
        name = pidf.stem
        log, _, exitf = _paths(name)
        if _alive(int(pidf.read_text().strip() or 0)):
            state = "RUNNING"
        elif exitf.exists():
            state = f"exited {exitf.read_text().strip()}"
        else:
            state = "gone"
        lines = len(log.read_text(errors="replace").splitlines()) if log.exists() else 0
        print(f"  {name:<24} {state:<12} {lines} log lines")
    return 0


def tail(name: str) -> int:
    log, _, _ = _paths(name)
    if not log.exists():
        print(f"no log for {name}", file=sys.stderr)
        return 1
    print(_tail_text(log, 40))
    return 0


def wait(name: str, secs: int) -> int:
    """Block until the job records an exit. Only when you genuinely must."""
    log, _, exitf = _paths(name)
    for _ in range(secs):
        if exitf.exists():
            code = int(exitf.read_text().strip() or 0)
            print(f"exited {code}")
            print(_tail_text(log, 10))
            return code
        time.sleep(1)
    print(
        f"{name} still running after {secs}s; it is NOT lost -- run --log {name}",
        file=sys.stderr,
    )
    return 124


def start(name: str, argv: list[str], cwd: str | None) -> int:
    """Start argv detached and return at once. The pid is recorded so it can be found again."""
    if not argv:
        print(f"run {name}: no command given", file=sys.stderr)
        return 2
    if cwd is not None and not os.path.isdir(cwd):
        # A command that runs in the wrong place is worse than one that refuses to start.
        print(f"run --cwd: no such directory: {cwd}", file=sys.stderr)
        return 2
    RUNS.mkdir(parents=True, exist_ok=True)
    log, pidf, exitf = _paths(name)
    exitf.unlink(missing_ok=True)
    wrapped = ["/bin/sh", "-c", _WRAPPER, "sh", *argv]
    env = {**os.environ, "EXIT_FILE": str(exitf)}
    with log.open("wb") as sink:
        child = subprocess.Popen(  # noqa: S603 -- argv is a LIST, never a shell string
            wrapped,
            stdout=sink,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=cwd,
            env=env,
            start_new_session=True,
        )
    pidf.write_text(str(child.pid))
    print(
        f"started {name}\n  pid {child.pid}\n  log {log}\n"
        f"  read it with:  run --log {name}\n  or wait:       run --wait {name}"
    )
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2
    verb = argv[0]
    if verb == "--status":
        return status(argv[1] if len(argv) > 1 else None)
    if verb == "--log":
        if len(argv) < 2:
            print("run --log <name>", file=sys.stderr)
            return 2
        return tail(argv[1])
    if verb == "--wait":
        if len(argv) < 2:
            print("run --wait <name> [secs]", file=sys.stderr)
            return 2
        return wait(argv[1], int(argv[2]) if len(argv) > 2 else 300)
    cwd = None
    if verb == "--cwd":
        # Consumed BEFORE the name, because that is the order the daemon passes it.
        if len(argv) < 4:
            print("run --cwd <dir> <name> <command...>", file=sys.stderr)
            return 2
        cwd, argv = argv[1], argv[2:]
        verb = argv[0]
    return start(verb, argv[1:], cwd)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

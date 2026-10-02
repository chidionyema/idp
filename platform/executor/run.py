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
import signal
import subprocess
import sys
import time
from pathlib import Path

RUNS = Path(os.environ.get("ESTATE_RUNS") or os.path.expanduser("~/.estate/runs"))

USAGE = (
    "run [--ceiling <secs>] <name> <command...> | run --status [name] | run --log <name> | "
    "run --wait <name> [secs] | run --cwd <dir> <name> <command...>"
)

# THE CEILING ENFORCER, AND WHY IT IS HERE (2026-10-02).
#
# The ceiling used to be `/usr/local/bin/timeout --signal=TERM <n>s ...`. Measured this turn,
# that file is not GNU `timeout`:
#
#     -rwxr-xr-x  306  /usr/local/bin/timeout   -> a BASH SHIM
#     #!/bin/bash
#     while [[ "$1" == --signal=* || "$1" == --kill-after=* ]]; do shift; done
#     secs="$1"; shift
#     exec perl -e 'alarm shift; exec @ARGV or exit 127' "$secs" "$@"
#
# Three defects in seven lines, each measured:
#   * `--signal=TERM` and `--kill-after` are consumed by the `while` loop and DISCARDED. The shim
#     accepts flags it does not implement, so a caller that sets a signal changes nothing.
#   * The real signal is `alarm()` in perl -- SIGALRM, 14 -- not SIGTERM. That is the
#     `Alarm clock: 14` in ~/.estate/runs/<job>.log and the `142` (128+14) exit code the daemon's
#     own comment already recorded, while naming profile slowness as the cause.
#   * `exec` replaces perl with the command, and the armed alarm survives the exec. The command
#     dies by SIGALRM, so the `_WRAPPER` below never reaches `echo $rc > "$EXIT_FILE"` -- no exit
#     file is written, and every downstream reader sees "no exit" as "killed" or "still running".
#
# The bound belongs where the pid and the exit file already live: here. This is the only process
# that is the command's parent, so it is the only one that can `waitpid` and record the REAL
# termination -- exit code, or 128+signal when a signal killed it. `timeout` is not used again;
# a bound enforced by a binary that lies about its signal is not a bound.
SUPERVISOR_FLAG = "--supervise"


def _exit_for(returncode: int) -> int:
    """A negative `Popen.returncode` is `-signum`; the shell convention is 128+signum."""
    return 128 + (-returncode) if returncode < 0 else returncode


def supervise(name: str, ceiling: int, argv: list[str], cwd: str | None) -> int:
    """Run the command in its own process group, bound it, and ALWAYS write the exit file.

    Called as `run.py --supervise <name> <ceiling> -- <command...>` in a session of its own. The
    command runs in a FURTHER process group so the whole tree (`bash -c` and everything it forks)
    can be signalled at once -- killing only the direct child leaves its children running, which is
    how a "bounded" job keeps burning the box.

    The timeout path sends SIGTERM, waits a short grace period, then SIGKILL. Both are REAL
    signals; neither is SIGALRM. The exit file is written on every path, including the signalled
    one, so "no exit file" stops meaning "killed" and starts meaning what it says.
    """
    if not argv:
        return 2
    log, pidf, exitf = _paths(name)
    RUNS.mkdir(parents=True, exist_ok=True)
    exitf.unlink(missing_ok=True)

    def _record(code: int) -> None:
        # The ONE place the exit file is written, so no return path can skip it.
        exitf.write_text(str(code))

    try:
        with log.open("ab") as sink:
            child = subprocess.Popen(  # noqa: S603 -- argv is a LIST, never a shell string
                argv,
                stdout=sink,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                cwd=cwd,
                start_new_session=True,
            )
    except OSError as exc:
        print(f"run: could not start the command: {exc}", file=sys.stderr)
        _record(127)
        return 127

    # The pid file names the COMMAND, not this supervisor: that is the handle a person kills, and
    # the handle `--status` checks for liveness.
    pidf.write_text(str(child.pid))
    try:
        code = _exit_for(child.wait(timeout=ceiling))
    except subprocess.TimeoutExpired:
        # Bound the WHOLE group, in two stages. SIGTERM first so the job runs its own cleanup;
        # SIGKILL after the grace window so a job that ignores SIGTERM still dies at the ceiling.
        #
        # A job WE killed records 124, whoever killed it and whatever code it died with. Recording
        # the raw 143 (128+SIGTERM) would make "the ceiling killed my job" and "my program exited
        # 143 itself" the same number -- and the first thing a caller does with a timed-out job is
        # ask which of those happened. 124 is `timeout`'s own convention for exactly this, so a
        # reader who knows the old system reads the same number; what changes is that it is now
        # honest and always written.
        _signal_group(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=_KILL_GRACE_SEC)
            print(
                f"run: {name} exceeded the {ceiling}s ceiling and was SIGTERMed",
                file=sys.stderr,
            )
        except subprocess.TimeoutExpired:
            _signal_group(child.pid, signal.SIGKILL)
            child.wait()
            print(
                f"run: {name} exceeded the {ceiling}s ceiling and was SIGKILLed",
                file=sys.stderr,
            )
        code = CEILING_EXIT
    _record(code)
    return 0


def _signal_group(pid: int, sig: int) -> None:
    """Signal the process GROUP led by `pid`, because `start_new_session` made it a leader.

    A signal to the pid alone leaves the command's own children alive. `killpg` reaches them all;
    when the group is already gone (the common race) that is not an error worth reporting.
    """
    try:
        os.killpg(os.getpgid(pid), sig)
    except (ProcessLookupError, PermissionError):
        try:
            os.kill(pid, sig)
        except OSError:
            pass


# How long a job gets to honour SIGTERM before SIGKILL. Long enough for a shell to run a trap,
# short enough that the ceiling is not quietly doubled by a job that ignores it.
_KILL_GRACE_SEC = int(os.environ.get("IDP_KILL_GRACE_SEC", "5"))

# The exit code a job gets when WE killed it at the ceiling. `timeout`'s convention. Distinct from
# any code a job returns on its own unless the job itself chooses 124, and the log line says which.
CEILING_EXIT = 124

# The wrapper that used to write the exit code is GONE (2026-10-02), and it is worth saying why,
# because it was the reason a killed job left no trace. It was:
#
#     _WRAPPER = 'a="$1"; shift; "$a" "$@"; rc=$?; echo $rc > "$EXIT_FILE"; exit $rc'
#
# The `echo $rc > "$EXIT_FILE"` needs the shell to SURVIVE the command. Under the perl-`alarm`
# shim, a job killed at the ceiling died by SIGALRM and took the shell with it, so that line never
# ran and `echo $rc > "$EXIT_FILE"` -- the only exit-file writer -- never executed. The exit file
# is now written by `supervise()` on every path, including the signalled one. Nothing here needs a
# shell to survive anything.


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


def start(name: str, argv: list[str], cwd: str | None, ceiling: int) -> int:
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
    # The supervisor IS the detached process; it owns the ceiling and the exit file. Launching it
    # with `start_new_session` is what makes it, and the command it leads, outlive this call.
    # `cwd` is passed through the environment rather than `Popen(cwd=)`: the supervisor must not
    # itself run in the target directory (its log/pid/exit paths are absolute anyway), and the
    # COMMAND is the thing that must run there. One field, one owner.
    sup = [
        sys.executable,
        os.path.abspath(__file__),
        SUPERVISOR_FLAG,
        name,
        str(ceiling),
        "--",
        *argv,
    ]
    env = {**os.environ, "RUN_CWD": cwd or ""}
    with log.open("wb") as sink:
        child = subprocess.Popen(  # noqa: S603 -- argv is a LIST, never a shell string
            sup,
            stdout=sink,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            env=env,
            start_new_session=True,
        )
    pidf.write_text(str(child.pid))
    print(
        f"started {name}\n  pid {child.pid}\n  log {log}\n"
        f"  ceiling {ceiling}s\n"
        f"  read it with:  run --log {name}\n  or wait:       run --wait {name}"
    )
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE, file=sys.stderr)
        return 2

    # The supervisor entry point, reached only from `start()`'s own argv: `--supervise <name>
    # <ceiling> -- <command...>`. It is checked first because a job's command may itself begin
    # with a word that looks like a verb (`run --status ...`), and argv order must not be able to
    # send a supervised job down the status path.
    if argv[0] == SUPERVISOR_FLAG:
        if len(argv) < 5 or "--" not in argv:
            print("run --supervise <name> <ceiling> -- <command...>", file=sys.stderr)
            return 2
        name = argv[1]
        try:
            ceiling = int(argv[2])
        except ValueError:
            print(
                f"run --supervise: ceiling must be an integer: {argv[2]!r}",
                file=sys.stderr,
            )
            return 2
        sep = argv.index("--")
        cwd = os.environ.get("RUN_CWD") or None
        return supervise(name, ceiling, argv[sep + 1 :], cwd)
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
    ceiling = (
        0  # 0 = unbounded, the pre-existing behaviour when no ceiling is asked for
    )
    while verb == "--ceiling":
        if len(argv) < 3:
            print("run --ceiling <secs> <name> <command...>", file=sys.stderr)
            return 2
        try:
            ceiling = int(argv[1])
        except ValueError:
            print(f"run --ceiling: not an integer: {argv[1]!r}", file=sys.stderr)
            return 2
        argv = argv[2:]
        verb = argv[0]

    # A leading `--`-prefixed word that matched none of the verbs above is a usage error, not a
    # command name. Without this guard `run -- foo` resolved `--` as an executable and reported
    # `No such file or directory: '--'`, which reads like a missing binary rather than a bad flag.
    # A real job name never starts with `--` (the daemon mints `exec-<ts>-<n>`), so refusing here
    # cannot reject a legitimate job; `--` before a command is only meaningful after
    # `--supervise` and `--cwd`, both handled above.
    if verb.startswith("--"):
        print(f"run: unknown option {verb!r}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    return start(verb, argv[1:], cwd, ceiling)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Contract execution: a PENDING action contract is handed to the estate's ONE executor.

WHY THIS FILE IS SMALL. Rule 6 of AGENTS.md: before building anything, prove it does not already
exist. It does. Measured 2026-09-20:

  `mcp/plugins/estate_executor.py` is "the one door an agent executes anything through". Its own
  docstring records the founder's instruction -- "find where we have done this, operationalise it"
  -- and its conclusion: `~/.pi/agent/bin/run` "already starts a command detached ... That is the
  executor, already proven, and this file calls it rather than writing a second one (LAW 43)".

  `extensions/dispatch/` already exposes `dispatch_job` to an agent with no wait path in its
  signature. That is the same boundary reached from the agent side; this is the same boundary
  reached from a contract.

So there is nothing here that starts a process. There is no `nohup`, no `Popen`, no `setsid`, no
scheduler, no second ledger. This module does three things and stops:

  1. it reads a PENDING contract from `action_contracts` (platform/intent/observer.py owns it);
  2. it composes the work from the contract's OWN then-clause and hands it to `execute_command`;
  3. it writes the job id and the terminal state back to the same row.

WHY THE CONTRACT CARRIES ITS COMMAND AND NOT A MODEL-GUESSED ONE. The Observer's job is to turn a
spoken request into a checkable contract; it is not trusted to author a shell command. So the
executor runs a command the person explicitly supplied -- `action_contracts.command` -- and refuses
a contract that has none. An executor that invented commands from a model's `then` clause would be
an unbounded mutation surface with a prose parser in front of it, which is the opposite of what
ADR 0025 exists for.

THE CEILING IS NOT OURS TO SET. `execute_command` clamps every request to the estate ceiling and
refuses a payload that declares it mutates the live worktree. Clamping again here would be a second
copy of a number -- signals.py's own docstring calls that "a second answer".

USAGE
  bin/contract-exec --tick                 # advance every runnable contract one step
  bin/contract-exec --dispatch <id>        # one contract
  bin/contract-exec --status               # what each contract is doing
  bin/contract-exec --tick --dry-run       # say what would run; dispatch nothing

EXIT 0 advanced (or nothing to do), 1 refused, 2 BLIND (the executor or the database is unreadable).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import sqlite3
import sys
from pathlib import Path
from typing import Any

# platform/intent/contract_exec.py -> repository root is THREE levels up (intent, platform, repo).
# `parents[1]` here resolved to `platform/` and produced `platform/platform/intent/observer.py`,
# which is the same off-by-one that made the Observer's own tests point outside the tree.
REPO = Path(__file__).resolve().parents[2]

# The one door. Loaded by path, with a fixed `sys.modules` name so two callers share one Executor
# registry -- the same trick routes.py and observer.py use, and load-bearing for the same reason:
# a second instance would own a second job registry, so `read_job` on one and `execute_command` on
# the other would report "no job with that id" about a job that exists.
_EXECUTOR_MODULE = REPO / "mcp" / "plugins" / "estate_executor.py"

_OBSERVER_MODULE = REPO / "platform" / "intent" / "observer.py"


class Refused(Exception):
    """A contract that cannot be run, and the reason is the caller's. Exit 1."""


class Blind(Exception):
    """The executor or the database cannot be read, so nothing is known. Exit 2."""


def _load(path: Path, name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover -- environment, not logic
        raise Blind(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _executor():
    """`estate_executor.py`, the one door. Never a local subprocess (LAW 43)."""
    try:
        return _load(_EXECUTOR_MODULE, "idp_estate_executor")
    except Exception as exc:  # noqa: BLE001
        raise Blind(f"the executor is not loadable: {exc}") from exc


def _observer():
    return _load(_OBSERVER_MODULE, "idp_intent_observer")


def _connect() -> sqlite3.Connection:
    """The same handle the Observer and signals.py use, so all three write one file."""
    return _observer()._connect()


# THE COMMAND IS A COLUMN THE PERSON FILLS, and it is added here rather than to the Observer's
# first migration because it is the executor's input, not the contract's shape: a contract records
# what was ASKED FOR, and whether a runnable command was supplied is a separate fact about whether
# it can be RUN. Additive, and NULL is meaningful -- a contract with no command is PENDING and
# unrunnable, which the board shows as such rather than as a failure.
_EXECUTOR_COLUMNS = (
    ("command", "TEXT"),
    ("job_id", "TEXT"),
    ("exit_code", "INTEGER"),
    ("dispatched_at", "TEXT"),
    ("finished_at", "TEXT"),
    # WHY THE REASON IS A COLUMN AND NOT ONLY A SIGNAL ROW. A refusal the executor made is the
    # single most useful thing a reader wants from a REFUSED contract, and it must survive the
    # signal being read (signals carry `read_at` and are a moment, not a state).
    ("error", "TEXT"),
)


def migrate(con: sqlite3.Connection) -> None:
    """The Observer's schema plus this module's additive columns. Idempotent.

    WHY ADDITIVE RATHER THAN ALTERED IN observer.py. A reader that has not been restarted still
    holds the old row shape; `ALTER TABLE ... ADD COLUMN` is what sqlite supports without a
    rewrite, and signals.py records the estate's convention that appended columns "are appended
    style because that is how they arrived (additive migrations)".
    """
    _observer()._migrate(con)
    have = {r["name"] for r in con.execute("PRAGMA table_info(action_contracts)")}
    for name, kind in _EXECUTOR_COLUMNS:
        if name not in have:
            con.execute(f"ALTER TABLE action_contracts ADD COLUMN {name} {kind}")
    con.commit()


def attach_command(con: sqlite3.Connection, contract_id: str, command: str) -> None:
    """Give a contract the command that will satisfy it. The person's, not a model's."""
    with con:
        cur = con.execute(
            "UPDATE action_contracts SET command = ?, updated_at = ? WHERE contract_id = ?",
            (command, _observer()._now(), contract_id),
        )
        if cur.rowcount == 0:
            raise Refused(f"no contract {contract_id}")


def compose(contract: dict[str, Any]) -> str:
    """The command a contract runs. Its own, or a refusal.

    IT DOES NOT BUILD A COMMAND FROM PROSE. The Observer's `then` is a checkable statement for a
    person to grade; it is not a shell string, and a function that turned it into one would be
    executing a language model's sentence on the founder's machine.
    """
    command = (contract.get("command") or "").strip()
    if not command:
        raise Refused(
            f"{contract['contract_id']} has no command. A contract records what was asked for; "
            "the command that satisfies it is supplied explicitly (bin/contract-exec --command). "
            "This refuses rather than composing one from the contract's then-clause."
        )
    return command


def _socket_path() -> Path:
    """The executor daemon's socket, resolved the way daemon.py resolves it.

    `IDP_EXECUTOR_SOCKET` first, because daemon.py honours that variable and a checker reading a
    different path would report BLIND while the daemon was answering on the one it was told to use.
    """
    return Path(os.environ.get("IDP_EXECUTOR_SOCKET") or (Path.home() / ".estate" / "executor.sock"))


def _daemon_is_up() -> bool:
    """Is anything listening? The file existing is not enough -- a stale socket outlives its daemon.

    A CONNECT, NOT AN `exists()`. daemon.py's socket is a file whose permissions are the access
    control, and a daemon killed with SIGKILL leaves the file behind; testing for the path would
    report a dead executor as alive, which is worse than not checking at all.
    """
    path = _socket_path()
    if not path.exists():
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(str(path))
        return True
    except OSError:
        return False


def dispatch(con: sqlite3.Connection, contract_id: str, *, dry_run: bool) -> str:
    """Hand one contract to the executor. Returns the new status."""
    obs = _observer()
    row = con.execute(
        "SELECT * FROM action_contracts WHERE contract_id = ?", (contract_id,)
    ).fetchone()
    if row is None:
        raise Refused(f"no contract {contract_id}")

    status = row["status"]
    if status in ("COMPLETED", "REFUSED"):
        # A TERMINAL CONTRACT IS NOT RE-DISPATCHED. Re-running finished work is how a retry loop
        # becomes an infinite spend, and the row's own state is the guard.
        return status
    if status == "RUNNING":
        return _poll(con, row, dry_run=dry_run)

    command = compose(dict(row))
    if dry_run:
        print(f"would dispatch {contract_id}: {command}", flush=True)
        return status

    ex = _executor()
    result = ex.execute_command(command)
    if not result.get("accepted"):
        # A REFUSAL IS NOT A FAILURE OF THIS CONTRACT. The executor refused the payload on its own
        # terms (unbounded, mutating the live worktree, empty). Recording it as RUNNING would be a
        # lie the board repeats; the status says REFUSED and the reason is in the row.
        reason = result.get("error", "the executor refused with no reason given")
        with con:
            con.execute(
                "UPDATE action_contracts SET status = 'REFUSED', updated_at = ?, error = ?"
                " WHERE contract_id = ?",
                (obs._now(), str(reason), contract_id),
            )
        print(f"REFUSE {contract_id}: {reason}", flush=True)
        return "REFUSED"

    job_id = result["job_id"]
    with con:
        con.execute(
            "UPDATE action_contracts SET status = 'RUNNING', job_id = ?, command = ?,"
            " dispatched_at = ?, updated_at = ? WHERE contract_id = ?",
            (job_id, command, obs._now(), obs._now(), contract_id),
        )
        # THE SIGNAL, so the reactor's node moves without the board polling the contracts table for
        # a reason. `kind` distinguishes it from the birth signal the Observer wrote.
        con.execute(
            "INSERT INTO fleetview_signals (session_id, runtime, kind, by, text, ok, created_at)"
            " VALUES (?, 'executor', 'dispatched', 'executor', ?, 1, ?)",
            (row["session_id"], f"{contract_id} -> {job_id}", obs._now()),
        )
    print(f"ok    {contract_id} dispatched as {job_id} (ceiling {result.get('ceiling_sec')}s)")
    return "RUNNING"


def _poll(con: sqlite3.Connection, row: sqlite3.Row, *, dry_run: bool) -> str:
    """Ask the executor what became of a dispatched job, and record the answer.

    THE EXECUTOR IS ASKED, NOT GUESSED. `read_job` reports `accepted` while the job runs -- there is
    no wait path anywhere in this design, because a door that waits is the thing dispatch replaced.
    A job the executor has forgotten (`found: False`) is left RUNNING and reported as such: the
    executor's registry is in-memory, so a daemon restart loses it, and inventing an outcome there
    would be a fabricated receipt.

    TWO DIFFERENT REASONS FOR THE SAME `RUNNING`, AND THEY ARE TOLD APART. "The daemon forgot this
    job" is a restart; "there is no daemon at all" is the whole execution plane being off, and it
    is the state this machine is actually in -- measured 2026-09-20, `bin/idp-executor-status`
    reports `MEASURED_FAIL no socket at ~/.estate/executor.sock`. Both leave the contract RUNNING,
    but a reader who sees the same words for both cannot tell a lost job from an estate where
    nothing can ever run. The socket is checked because its absence is a knowable fact.
    """
    job_id = row["job_id"]
    if not job_id or dry_run:
        return row["status"]
    if not _daemon_is_up():
        # NOT A FAILURE OF THIS CONTRACT. Say so once per poll and leave the row alone: marking it
        # BLOCKED would blame the contract for an estate-wide outage, and the status tool already
        # names the real cause.
        print(
            f"BLIND {row['contract_id']}: no executor daemon at {_socket_path()} -- nothing can run. "
            "Start it with bin/exec-daemon; bin/idp-executor-status reports the socket.",
            file=sys.stderr,
        )
        return "RUNNING"
    result = _executor().read_job(job_id)
    if not result.get("found"):
        print(f"note  {row['contract_id']}: executor does not know {job_id}; left RUNNING")
        return "RUNNING"
    if result.get("state") == "accepted":
        return "RUNNING"

    exit_code = result.get("exit_code")
    # THE CONTRACT IS COMPLETED WHEN THE COMMAND SUCCEEDED, which is the only fact the executor
    # actually supplies. It is NOT proof the then-clause holds -- that is a grader's job and this
    # file does not claim it. Stated rather than implied: a green node here means "the command
    # exited 0", and a board that reads it as "the outcome was verified" would be reading more
    # than is written.
    status = "COMPLETED" if exit_code == 0 else "BLOCKED"
    with con:
        con.execute(
            "UPDATE action_contracts SET status = ?, exit_code = ?, finished_at = ?, updated_at = ?"
            " WHERE contract_id = ?",
            (status, exit_code, _observer()._now(), _observer()._now(), row["contract_id"]),
        )
    print(f"ok    {row['contract_id']} -> {status} (exit {exit_code})")
    return status


def tick(con: sqlite3.Connection, *, dry_run: bool, limit: int) -> int:
    """Advance every runnable contract one step. One step, never a loop that waits."""
    rows = con.execute(
        "SELECT * FROM action_contracts WHERE status IN ('PENDING', 'RUNNING')"
        " ORDER BY created_at LIMIT ?",
        (limit,),
    ).fetchall()
    if not rows:
        return 0
    moved = 0
    for row in rows:
        try:
            dispatch(con, row["contract_id"], dry_run=dry_run)
            moved += 1
        except Refused as exc:
            # ONE BAD CONTRACT DOES NOT STOP THE OTHERS. An unrunnable row is a fact about that row,
            # and the tick's job is to advance what it can while saying so.
            print(f"REFUSE {row['contract_id']}: {exc}", file=sys.stderr)
    return moved


def status(as_json: bool) -> int:
    con = _connect()
    migrate(con)
    rows = con.execute(
        "SELECT contract_id, status, command, job_id, exit_code, created_at, finished_at"
        " FROM action_contracts ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    if as_json:
        print(json.dumps([dict(r) for r in rows], indent=2))
        return 0
    if not rows:
        print("no contracts to execute -- nothing has been addressed to the agents")
        return 0
    for r in rows:
        extra = f" job={r['job_id']}" if r["job_id"] else ""
        code = f" exit={r['exit_code']}" if r["exit_code"] is not None else ""
        print(f"{r['contract_id']}  {r['status']:<9}{extra}{code}")
        if r["command"]:
            print(f"    $ {r['command']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="contract-exec",
        description="Hand a tracked action contract to the estate's one executor.",
    )
    p.add_argument("--tick", action="store_true", help="advance every runnable contract one step")
    p.add_argument("--dispatch", metavar="CONTRACT_ID", help="dispatch one contract")
    p.add_argument("--command", metavar="SHELL", help="attach a command to a contract")
    p.add_argument("--status", action="store_true", help="what each contract is doing")
    p.add_argument("--json", action="store_true", help="with --status, emit JSON")
    p.add_argument("--dry-run", action="store_true", help="say what would run; dispatch nothing")
    p.add_argument("--limit", type=int, default=10, help="contracts per tick")
    args = p.parse_args(argv)

    try:
        if args.status:
            return status(args.json)
        con = _connect()
        migrate(con)
        if args.command:
            if not args.dispatch:
                raise Refused("--command needs --dispatch <contract_id>")
            attach_command(con, args.dispatch, args.command)
            print(f"ok    {args.dispatch} now carries a command")
            return 0
        if args.dispatch:
            dispatch(con, args.dispatch, dry_run=args.dry_run)
            return 0
        if args.tick:
            moved = tick(con, dry_run=args.dry_run, limit=args.limit)
            print(f"{moved} contract(s) advanced")
            return 0
        p.print_help()
        return 1
    except Refused as exc:
        print(f"REFUSE contract-exec: {exc}", file=sys.stderr)
        return 1
    except Blind as exc:
        print(f"BLIND  contract-exec: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

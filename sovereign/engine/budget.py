"""The budget row and its optimistic lock (R29, spec 4.3).

Spec 4.3: "Every transition consumes tokens from the pre-allocated budget.
Budget is enforced with optimistic locking (prevents race conditions). At
zero, hard halt. No 'ask for more.'"

Before this file, engine/workflow.py held the balance in a workflow
attribute and subtracted from it. Inside one workflow that is genuinely
race-free -- a Temporal workflow is single-threaded -- but the race the
spec names is not there. It is between *activities*, which run
concurrently on the worker's event loop and, for cp31's own scenario,
"two activities spend from one budget at the same time". A workflow
attribute cannot see that. A row with a version column can.

The lock is compare-and-swap, not a mutex:

    UPDATE budget SET remaining = ?, version = version + 1
     WHERE session_id = ? AND version = ?

A concurrent writer that got there first has bumped `version`, the UPDATE
matches zero rows, and this caller re-reads and retries. Nothing is ever
held, so nothing can deadlock, and a crashed caller leaves no lock behind
-- which is the actual reason to prefer optimistic locking here over
`BEGIN IMMEDIATE`.

The store is sqlite (config.budget.db_filename). Chosen, not written:
sqlite gives durability, a real transaction and a row version for free,
it is already this estate's embedded store (the sidecar mirrors one), and
it needs no daemon. A hand-rolled lock file would have been the LAW 43
violation.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sovereign import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS budget (
    session_id TEXT PRIMARY KEY,
    total      INTEGER NOT NULL,
    remaining  INTEGER NOT NULL,
    version    INTEGER NOT NULL
)
"""


class BudgetContention(RuntimeError):
    """budget.max_cas_retries compare-and-swap attempts all lost."""


@dataclass(frozen=True)
class Spend:
    session_id: str
    requested: int
    spent: int
    remaining: int
    version: int
    halted: bool
    attempts: int


def db_path() -> Path:
    return Path(config.BUDGET_DB)


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=config.BUDGET_BUSY_TIMEOUT_MS / config.MS_PER_SECOND)
    conn.execute(f"PRAGMA busy_timeout = {int(config.BUDGET_BUSY_TIMEOUT_MS)}")
    conn.execute(_SCHEMA)
    return conn


def allocate(session_id: str, total: int) -> Spend:
    """Pre-allocate a session's budget. Idempotent: re-allocating the same
    session leaves the existing row alone, so a workflow replay or a
    retried activity cannot silently refill anyone."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO budget (session_id, total, remaining, version) VALUES (?, ?, ?, 0)",
            (session_id, int(total), int(total)),
        )
        return read(session_id, _conn=conn)
    finally:
        conn.close()


def read(session_id: str, *, _conn: sqlite3.Connection | None = None) -> Spend:
    conn = _conn or _connect()
    try:
        row = conn.execute(
            "SELECT total, remaining, version FROM budget WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return Spend(session_id, 0, 0, 0, 0, True, 0)
        total, remaining, version = int(row[0]), int(row[1]), int(row[2])
        return Spend(session_id, 0, 0, remaining, version, remaining <= 0, 0)
    finally:
        if _conn is None:
            conn.close()


def spend(session_id: str, tokens: int) -> Spend:
    """Take `tokens` from the row, never below zero, under compare-and-swap.

    The clamp is the hard halt: a spend larger than the balance takes the
    balance to exactly zero and returns halted=True with `spent` recording
    what was actually taken. cp31's property -- "the final balance equals
    start minus both spends, never negative" -- is the test, in
    test_budget.py, driven from real threads."""
    want = max(int(tokens), 0)
    conn = _connect()
    try:
        for attempt in range(1, config.BUDGET_MAX_CAS_RETRIES + 1):
            row = conn.execute(
                "SELECT total, remaining, version FROM budget WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None:
                return Spend(session_id, want, 0, 0, 0, True, attempt)
            total, remaining, version = int(row[0]), int(row[1]), int(row[2])
            taken = min(want, remaining)
            new_remaining = remaining - taken
            cur = conn.execute(
                "UPDATE budget SET remaining = ?, version = version + 1 "
                "WHERE session_id = ? AND version = ?",
                (new_remaining, session_id, version),
            )
            if cur.rowcount == 1:
                return Spend(session_id, want, taken, new_remaining, version + 1, new_remaining <= 0, attempt)
        raise BudgetContention(
            f"{config.BUDGET_MAX_CAS_RETRIES} compare-and-swap attempts lost for session {session_id!r}"
        )
    finally:
        conn.close()


def refill(session_id: str, tokens: int) -> Spend:
    """Add to both total and remaining under the same compare-and-swap."""
    add = max(int(tokens), 0)
    conn = _connect()
    try:
        for attempt in range(1, config.BUDGET_MAX_CAS_RETRIES + 1):
            row = conn.execute(
                "SELECT total, remaining, version FROM budget WHERE session_id = ?", (session_id,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT OR IGNORE INTO budget (session_id, total, remaining, version) VALUES (?, ?, ?, 0)",
                    (session_id, add, add),
                )
                return read(session_id, _conn=conn)
            total, remaining, version = int(row[0]), int(row[1]), int(row[2])
            cur = conn.execute(
                "UPDATE budget SET total = ?, remaining = ?, version = version + 1 "
                "WHERE session_id = ? AND version = ?",
                (total + add, remaining + add, session_id, version),
            )
            if cur.rowcount == 1:
                return Spend(session_id, 0, 0, remaining + add, version + 1, False, attempt)
        raise BudgetContention(
            f"{config.BUDGET_MAX_CAS_RETRIES} compare-and-swap attempts lost for session {session_id!r}"
        )
    finally:
        conn.close()


def as_dict(s: Spend) -> dict[str, Any]:
    return {
        "session_id": s.session_id,
        "requested": s.requested,
        "spent": s.spent,
        "remaining": s.remaining,
        "version": s.version,
        "halted": s.halted,
        "attempts": s.attempts,
    }

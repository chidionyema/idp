"""FleetView item #6: nudge a stale session.

Investigation for the notes mailbox (`src/notes.py`, `docs/founder/fleetview-voice-revisit.md`)
found no live delivery path into a *running* process for most runtimes -- but `sovereign` is the
one exception: `sovereign/engine/client.signal(session_id, "steer", by, text)` sends a real
Temporal signal to a live workflow (`sovereign/engine/workflow.py`'s `steer()` queues the text and
it is read at the session's next step, `sb steer <session_id>` is the same call from the CLI).
This module is that same, already-real mechanism, reached from a board button instead of a
terminal -- not a new intervention, a new door onto one that already exists.

Scope, deliberately narrow (founder: "get all done", scoped down to what is real): only `steer`
is wired, and only for `runtime == "sovereign"` -- the one runtime with a live signal to send it
to. A runtime with no such mechanism gets an honest `UnsupportedRuntime`, never a button that
looks like it worked and did nothing.

No portal-identity auth is wired here yet (CP3's "unauthenticated caller gets 401" is a separate,
larger checkpoint -- full portal identity has to reach this standalone Python process, which does
not exist today). Until then this follows the same bar `notes.py` already sets for its own writes:
a non-blank, attributed `by`, not a cryptographic identity. Documented here so it is a known gap,
not a hidden one.

Storage: `catalog/estate.db` (THE HEADLINE -- extended, not duplicated), a new `fleetview_signals`
table alongside notes.py's `session_notes`, named `fleetview_signals` to match the audit row CP3's
own feature file (`features/fleetview/cp3_signals.feature`) names. Every dispatch attempt is
recorded, success or failure, once the input itself has passed validation -- an invalid request
(missing session_id, blank `by`, ...) never touched a real session and leaves no row, the same
rule `notes.py`'s `InvalidNote` follows.

CONFIG (LAW 46): ESTATE_DB, default `<repo>/catalog/estate.db` -- same variable and default
`notes.py` and `bin/estate-twin-runtime` read.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import os
import sqlite3
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_DB_DEFAULT = _ROOT / "catalog" / "estate.db"

MAX_TEXT_LENGTH = 4000
DEFAULT_NUDGE_TEXT = "Nudge from FleetView: this session has been idle. Please post a status, or wrap up."

# Only sovereign has a live signal path today (see module docstring). Extend this set the day a
# second runtime grows one -- never fake a delivery for a runtime not in it.
_SUPPORTED_RUNTIMES = frozenset({"sovereign"})


class InvalidSignal(ValueError):
    """Raised for a request that never touched a real session -- routes.py turns this into 400."""


class UnsupportedRuntime(ValueError):
    """Raised for a runtime with no live signal path -- routes.py turns this into 422."""


def _db_path() -> Path:
    return Path(os.environ.get("ESTATE_DB", str(_DB_DEFAULT)))


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(_db_path()))
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS fleetview_signals (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            runtime    TEXT NOT NULL,
            kind       TEXT NOT NULL,
            by         TEXT NOT NULL,
            text       TEXT NOT NULL,
            ok         INTEGER NOT NULL,
            error      TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS fleetview_signals_session "
        "ON fleetview_signals (session_id, runtime, created_at)"
    )
    return con


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "runtime": row["runtime"],
        "kind": row["kind"],
        "by": row["by"],
        "text": row["text"],
        "ok": bool(row["ok"]),
        "error": row["error"],
        "created_at": row["created_at"],
    }


def _record(
    session_id: str,
    runtime: str,
    kind: str,
    by: str,
    text: str,
    ok: bool,
    error: str | None,
) -> dict[str, Any]:
    with _connect() as con:
        cur = con.execute(
            "INSERT INTO fleetview_signals "
            "(session_id, runtime, kind, by, text, ok, error, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, runtime, kind, by, text, 1 if ok else 0, error, _now()),
        )
        row = con.execute(
            "SELECT * FROM fleetview_signals WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _row_to_dict(row)


def _dispatch_steer(session_id: str, by: str, text: str) -> str | None:
    """Send the real Temporal steer signal. Returns None on success, an error string on failure --
    never raises, so the caller always gets to record the attempt."""
    try:
        from sovereign.engine import client as engine_client
    except ImportError as exc:
        return f"sovereign engine not importable here: {exc}"
    try:
        result = asyncio.run(engine_client.signal(session_id, "steer", by, text))
    except Exception as exc:  # noqa: BLE001 - a dead workflow/handle is a fact to report, not hide
        return f"{exc.__class__.__name__}: {exc}"
    if not result.get("ok", False):
        return str(result.get("error") or "signal rejected")
    return None


def nudge(session_id: str, runtime: str, by: str, text: str = "") -> dict[str, Any]:
    """Steer a session with a nudge message and record the attempt.

    Raises InvalidSignal for input that never reaches a real session (nothing recorded), and
    UnsupportedRuntime for a runtime with no live signal path (nothing recorded -- there is no
    session to have attempted anything against). A reachable session that the signal itself fails
    against still gets a row, with ok=False and the real error, because a real attempt was made.
    """
    session_id = (session_id or "").strip()
    runtime = (runtime or "").strip()
    by = (by or "").strip()
    text = (text or "").strip() or DEFAULT_NUDGE_TEXT
    if not session_id:
        raise InvalidSignal("session_id is required")
    if not runtime:
        raise InvalidSignal("runtime is required")
    if not by:
        raise InvalidSignal("by is required")
    if len(text) > MAX_TEXT_LENGTH:
        raise InvalidSignal(f"text exceeds {MAX_TEXT_LENGTH} characters")
    if runtime not in _SUPPORTED_RUNTIMES:
        raise UnsupportedRuntime(f"{runtime} has no live signal path yet")

    error = _dispatch_steer(session_id, by, text)
    return _record(
        session_id, runtime, "steer", by, text, ok=error is None, error=error
    )


def signals_for(session_id: str) -> list[dict[str, Any]]:
    """Every signal attempt recorded for a session, newest first -- the audit trail a board row
    can show, mirroring notes_for's read-back in notes.py."""
    session_id = (session_id or "").strip()
    if not session_id:
        return []
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM fleetview_signals WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]

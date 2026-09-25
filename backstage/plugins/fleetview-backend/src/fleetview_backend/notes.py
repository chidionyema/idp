"""FleetView notes: leave a note for a session, any runtime, read later.

The founder asked to interact with running sessions, including by voice. Investigation (recorded
`docs/founder/fleetview-voice-revisit.md`) found no live, cross-runtime delivery path exists
anywhere in the estate today -- not for voice, and not even a text injection API a page could call
into a *running* process, for any runtime. What is real and buildable now is the other half of
"interact": a message a person leaves against a session id that the session (or its next reader)
picks up later. Founder, when offered a claude-code-only or idp-repo-scoped version of this:
"we are model agnostic and this is enterprise wide, not repo wide" -- so this is keyed by
`(session_id, runtime)`, works the same for a runtime that does not exist yet, and lives in the
estate's one graph store rather than a new one (THE HEADLINE).

Delivery is honestly async, not live: a note sits here until something reads it. No runtime reads
this table automatically today (a claude-code SessionStart hook that tailed it would be the next
buildable step -- see the revisit doc -- but that is a separate, opt-in change to a person's own
session config, not this module's job). This module only owns the write and the read-back that
FleetView itself uses to show notes on the board.

Storage: `catalog/estate.db`, the estate's one asset/graph database (extended, not duplicated --
`bin/estate-twin-runtime` owns `nodes`/`edges`/`node_events` in the same file; this module owns
its own table the same way `mcp/plugins/estate_state.py` and `bin/rca_worker` own theirs). A
session id is not an estate-graph node id, so `nodes`/`node_events` would need a fabricated
mapping to reuse -- a new, narrow table is the honest choice, not a second store.

CONFIG (LAW 46): ESTATE_DB, default `<repo>/catalog/estate.db` (same variable and default
`bin/estate-twin-runtime` reads).
"""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_DB_DEFAULT = _ROOT / "catalog" / "estate.db"

MAX_NOTE_LENGTH = 4000


def _db_path() -> Path:
    return Path(os.environ.get("ESTATE_DB", str(_DB_DEFAULT)))


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(_db_path()))
    con.row_factory = sqlite3.Row
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS session_notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            runtime    TEXT NOT NULL,
            note       TEXT NOT NULL,
            author     TEXT NOT NULL,
            created_at TEXT NOT NULL,
            read_at    TEXT
        )
        """
    )
    con.execute(
        "CREATE INDEX IF NOT EXISTS session_notes_session "
        "ON session_notes (session_id, runtime, created_at)"
    )
    return con


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "runtime": row["runtime"],
        "note": row["note"],
        "author": row["author"],
        "created_at": row["created_at"],
        "read_at": row["read_at"],
    }


class InvalidNote(ValueError):
    """Raised for a note the caller cannot have meant -- routes.py turns this into a 400."""


def add_note(session_id: str, runtime: str, note: str, author: str) -> dict[str, Any]:
    """Write one note against a (session_id, runtime) pair. Returns the stored record.

    All four fields are required and non-blank: a note with no author cannot be attributed, and a
    note with no runtime cannot be shown only where it belongs once more than one runtime is real
    here -- exactly the ambiguity the founder rejected a repo/runtime-scoped design over.
    """
    session_id = (session_id or "").strip()
    runtime = (runtime or "").strip()
    note = (note or "").strip()
    author = (author or "").strip()
    if not session_id:
        raise InvalidNote("session_id is required")
    if not runtime:
        raise InvalidNote("runtime is required")
    if not note:
        raise InvalidNote("note is required")
    if len(note) > MAX_NOTE_LENGTH:
        raise InvalidNote(f"note exceeds {MAX_NOTE_LENGTH} characters")
    if not author:
        raise InvalidNote("author is required")

    with _connect() as con:
        cur = con.execute(
            "INSERT INTO session_notes (session_id, runtime, note, author, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, runtime, note, author, _now()),
        )
        row = con.execute(
            "SELECT * FROM session_notes WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _row_to_dict(row)


def notes_for(session_id: str, runtime: str | None = None) -> list[dict[str, Any]]:
    """Every note left for a session, oldest first (a thread, not a stack).

    `runtime` narrows to one runtime's notes when a caller already knows it; omitted, every note
    for that session_id across every runtime comes back, since a session id can outlive a runtime
    rename and a board should not hide a note over that.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        return []
    with _connect() as con:
        if runtime:
            rows = con.execute(
                "SELECT * FROM session_notes WHERE session_id = ? AND runtime = ? "
                "ORDER BY created_at ASC",
                (session_id, runtime.strip()),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM session_notes WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
    return [_row_to_dict(r) for r in rows]

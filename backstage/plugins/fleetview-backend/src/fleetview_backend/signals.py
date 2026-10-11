"""FleetView item #6: nudge a stale session.

Investigation for the notes mailbox (`src/notes.py`, `docs/founder/fleetview-voice-revisit.md`)
found no live delivery path into a *running* process for most runtimes -- but `sovereign` is the
one exception: `sovereign/engine/client.signal(session_id, "steer", by, text)` sends a real
Temporal signal to a live workflow (`sovereign/engine/workflow.py`'s `steer()` queues the text and
it is read at the session's next step, `sb steer <session_id>` is the same call from the CLI).
This module is that same, already-real mechanism, reached from a board button instead of a
terminal -- not a new intervention, a new door onto one that already exists.

CP8 extends this to all four runtimes. Each runtime uses its own native channel:
- `sovereign`: Temporal signal (unchanged)
- `claude-code`: filesystem mailbox at ~/.claude/state/directives/<uuid>.json, read at next
  SessionStart/PostCompact hook (next-turn delivery; mid-turn terminal-UI path cannot be scripted)
- `otto`: NATS steer event on estate.agent.otto.<session_id>.steer (Otto's adapter delivers as
  Telegram)
- `cyrus`: Linear GraphQL commentCreate mutation on the session's issue

A runtime with no live signal path gets an honest `UnsupportedRuntime`, never a button that
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

CONFIG (LAW 46):
  ESTATE_DB            -- default `<repo>/catalog/estate.db`
  FLEETVIEW_DB         -- optional; when set, the tables THIS module owns live there instead
                          (the cluster sets it to a writable volume; ESTATE_DB stays the
                          read-only catalogue snapshot). Unset on the laptop: no change.
  ESTATE_STATE_PATH_PREFIX -- ledger root, default ~/.claude/state/prompt-ledger/; directives dir
                              is derived as <ledger_root>/../directives/
  NATS_URL             -- default nats://nats.event-bus.svc:4222
  LINEAR_API_KEY       -- Linear API token (or LINEAR_API_KEY_FILE path)
  LINEAR_API_KEY_FILE  -- path to file containing the Linear API token
"""

from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import os
import sqlite3
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[5]
_DB_DEFAULT = _ROOT / "catalog" / "estate.db"


def _db_path() -> Path:
    """Where THIS module's tables live -- preferring FLEETVIEW_DB over ESTATE_DB.

    WHY A SECOND KNOB. In the cluster, ESTATE_DB points at the catalogue snapshot the
    fetch-estate-db init container ships, and that volume is read-only ON PURPOSE: the shipped
    catalogue is an artifact, not a database this pod writes. The fleetview's own tables
    (fleetview_signals/_replies/_work) must still be writable, so the overlay gives the sidecar a
    writable emptyDir and points FLEETVIEW_DB at it -- measured 2026-10-11: with only ESTATE_DB
    set, GET /work answered 500 `attempt to write a readonly database` while /sessions served
    200 off the same snapshot. On the laptop neither variable is special: FLEETVIEW_DB is unset,
    the ESTATE_DB fallback holds, and everything stays one database, exactly as before.
    """
    raw = (
        os.environ.get("FLEETVIEW_DB", "").strip()
        or os.environ.get("ESTATE_DB", "").strip()
    )
    return Path(raw) if raw else _DB_DEFAULT


MAX_TEXT_LENGTH = 4000
DEFAULT_NUDGE_TEXT = "Nudge from FleetView: this session has been idle. Please post a status, or wrap up."

_LINEAR_API = "https://api.linear.app/graphql"

_SUPPORTED_RUNTIMES = frozenset({"sovereign", "claude-code", "otto", "cyrus"})


class InvalidSignal(ValueError):
    """Raised for a request that never touched a real session -- routes.py turns this into 400."""


class UnsupportedRuntime(ValueError):
    """Raised for a runtime with no live signal path -- routes.py turns this into 422."""


_SIGNALS_DDL = """
    CREATE TABLE IF NOT EXISTS fleetview_signals (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        runtime    TEXT NOT NULL,
        kind       TEXT NOT NULL,
        by         TEXT NOT NULL,
        text       TEXT NOT NULL,
        ok         INTEGER NOT NULL,
        error      TEXT,
        created_at TEXT NOT NULL,
        -- When the session's own hook CONSUMED the directive. NULL means written and not yet read,
        -- which is a different fact from ok=0 (the write failed).
        read_at    TEXT
    )
"""
_REPLIES_DDL = """
    CREATE TABLE IF NOT EXISTS fleetview_replies (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        runtime    TEXT NOT NULL,
        -- "agent" for the session's own output, a name for a person.
        author     TEXT NOT NULL,
        text       TEXT NOT NULL,
        -- The steer this answers, when the session knows. NULL for an unsolicited update.
        in_reply_to INTEGER,
        created_at TEXT NOT NULL
    )
"""
_WORK_DDL = """
    CREATE TABLE IF NOT EXISTS fleetview_work (
        session_id TEXT PRIMARY KEY,
        runtime    TEXT NOT NULL,
        branch     TEXT NOT NULL DEFAULT '',
        step       TEXT NOT NULL DEFAULT '',
        -- The session's own process id, reported once at startup. ITS OWN COLUMN, because `step`
        -- is overwritten on every tool call: encoded as "pid 1234" in the step text it survived
        -- exactly until the agent ran anything.
        pid        INTEGER,
        updated_at TEXT NOT NULL
    )
"""

_SCHEMA_READY: set[str] = set()


def _ensure_schema(con: sqlite3.Connection) -> None:
    """Create every table this module owns, ONCE per database path per process.

    CALLED FROM `_connect` SO NO CALLER HAS TO REMEMBER. That is deliberate: the previous shape had
    each function calling its own `_ensure_*`, and when one refactor removed the inline `CREATE`
    from `_connect` the signals table stopped being created for any FRESH database -- while every
    existing database kept working, so every test passed. Found by creating a fresh database on
    purpose. One place, reached by every path, is the fix that cannot rot that way.

    The additive migrations are kept: a database created by an older version still works.
    """
    key = str(_db_path())
    if key in _SCHEMA_READY:
        return
    con.execute(_SIGNALS_DDL)
    con.execute(
        "CREATE INDEX IF NOT EXISTS fleetview_signals_session "
        "ON fleetview_signals (session_id, runtime, created_at)"
    )
    con.execute(_REPLIES_DDL)
    con.execute(
        "CREATE INDEX IF NOT EXISTS fleetview_replies_session "
        "ON fleetview_replies (session_id, created_at)"
    )
    con.execute(_WORK_DDL)
    # Additive migrations, each guarded by reading the table's own columns so they are idempotent
    # and cannot fail on a fresh database.
    for table, column, decl in (
        ("fleetview_signals", "read_at", "TEXT"),
        ("fleetview_work", "pid", "INTEGER"),
    ):
        try:
            cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
            if cols and column not in cols:
                con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
        except sqlite3.Error:
            pass
    _SCHEMA_READY.add(key)


@contextlib.contextmanager
def _connect():
    """A connection that is COMMITTED AND CLOSED, and that can share the file.

    TWO DEFECTS FIXED HERE, both found by review 2026-09-20.

    1. `with sqlite3.connect(...) as con:` DOES NOT CLOSE THE CONNECTION. sqlite3's connection
       context manager commits or rolls back a transaction and nothing else -- the file descriptor
       is released only by refcounting, and every call site in this module used that form. Under
       load, or on any path that held a reference, descriptors accumulated.

    2. NO WAL, NO BUSY TIMEOUT. Two processes write this database (the Fleetview backend and the
       voice service), and the default rollback journal takes an exclusive lock for every write, so
       a concurrent reader or writer raises `database is locked`. Worse, `_record` had no handler
       for it: a steer, a reply, or a KILL could complete its side effect and then report 500,
       because the audit row failed after the deed was done.

    WAL lets readers and one writer work concurrently; `busy_timeout` waits rather than failing.
    `check_same_thread=False` because the FastAPI handlers run in a threadpool.
    """
    con = sqlite3.connect(str(_db_path()), timeout=5.0, check_same_thread=False)
    con.row_factory = sqlite3.Row
    # PRAGMAs are per-connection except journal_mode, which is per-database and persists -- setting
    # it repeatedly is harmless and is what makes a fresh database correct on first write.
    # SCHEMA ONCE PER PROCESS, here, so no caller has to remember. This also means a fresh
    # database is complete on the first connection rather than depending on which function ran
    # first -- which is exactly how a missing table survives testing.
    _ensure_schema(con)
    try:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
        con.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error:
        # A read-only or exotic filesystem refuses these. Not fatal: the connection still works,
        # just with the old locking behaviour, and refusing to start would be worse.
        pass
    try:
        yield con
        con.commit()
    except Exception:
        try:
            con.rollback()
        except sqlite3.Error:
            pass
        raise
    finally:
        # THE PART THE OLD FORM NEVER DID.
        try:
            con.close()
        except sqlite3.Error:
            pass


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """One audit row as the API returns it.

    `read_at` is the acknowledgement: when the session's own hook consumed the directive. It is
    delivered alongside `ok` because the two answer DIFFERENT questions and conflating them is
    what made the board lie. `ok` describes the WRITE (did the channel accept the dispatch),
    `read_at` describes the READ (did the agent see it).

    Read with `.keys()` rather than `row["read_at"]` because this function is also reached by
    a database created before the column existed, and a missing acknowledgement must read as
    absent, not raise.
    """
    keys = row.keys()
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
        "read_at": row["read_at"] if "read_at" in keys else None,
        # The two-part verdict the board actually renders, so the page does not have to infer
        # it from two nullable fields and get it wrong. Never a third state: 'sent' and 'read'
        # are the only things the tables can prove.
        "acknowledged": bool("read_at" in keys and row["read_at"]),
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


def _dispatch_steer_sovereign(session_id: str, by: str, text: str) -> str | None:
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


def _dispatch_steer_claude_code(session_id: str, by: str, text: str) -> str | None:
    """Write the steer text to ~/.claude/state/directives/<raw_uuid>.json.

    `session_id` format is `<repo_or_stem>:<raw_uuid>` -- split on the last colon.
    The claude-code session reads this mailbox at the next SessionStart or PostCompact hook.
    Delivery is next-turn, not mid-turn (the mid-turn terminal-UI path cannot be scripted).
    Returns None on success, error string on failure.

    CONFIG: ESTATE_STATE_PATH_PREFIX -- the ledger root, default ~/.claude/state/prompt-ledger/.
    The directives dir is derived as <ledger_root>/../directives/.
    """
    # Parse the raw uuid from the last colon
    raw_uuid = session_id.rsplit(":", 1)[-1]

    # Derive directives dir from config
    ledger_root = Path(
        os.environ.get(
            "ESTATE_STATE_PATH_PREFIX",
            os.path.expanduser("~/.claude/state/prompt-ledger/"),
        )
    )
    directives_dir = ledger_root.parent / "directives"

    try:
        os.makedirs(directives_dir, exist_ok=True)
        payload = {
            "session_id": session_id,
            "by": by,
            "text": text,
            "written_at": _now(),
        }
        dest = directives_dir / f"{raw_uuid}.json"
        dest.write_text(json.dumps(payload), encoding="utf-8")
    except OSError as exc:
        return f"OSError writing directive: {exc}"
    return None


def _dispatch_steer_otto(session_id: str, by: str, text: str) -> str | None:
    """Publish a NATS steer event for Otto. Otto's adapter delivers it as a Telegram message.

    Requires NATS_URL to be set. If not set, returns an error string (never silently drops).
    Subject: estate.agent.otto.<session_id>.steer
    Payload matches estate.agent.event.json schema (kind=steer, runtime=otto).

    CONFIG: NATS_URL -- default nats://nats.event-bus.svc:4222
    """
    try:
        import nats  # type: ignore[import]
    except ImportError as exc:
        return f"nats library not importable: {exc}"

    nats_url = os.environ.get("NATS_URL", "nats://nats.event-bus.svc:4222")
    if not os.environ.get("NATS_URL"):
        return "NATS_URL not configured — cannot reach Otto"

    subject = f"estate.agent.otto.{session_id}.steer"
    payload = {
        "session_id": session_id,
        "runtime": "otto",
        "kind": "steer",
        "at": _now(),
        "phase": "executing",
        "steer": {
            "text": text,
            "author": by,
            "audit_row": None,
        },
    }
    data = json.dumps(payload).encode()

    async def _publish() -> None:
        nc = await nats.connect(nats_url)
        try:
            await nc.publish(subject, data)
            await nc.flush()
        finally:
            await nc.close()

    try:
        asyncio.run(_publish())
    except Exception as exc:  # noqa: BLE001
        return f"{exc.__class__.__name__}: {exc}"
    return None


def _dispatch_steer_cyrus(session_id: str, by: str, text: str) -> str | None:
    """Post a Linear comment on the Cyrus session's issue.

    Parses the Linear issue ID from session_id (format: <issue_id>:<uuid> or <slug>:<uuid>).
    Uses the Linear GraphQL API (https://api.linear.app/graphql) to post a comment.

    CONFIG: LINEAR_API_KEY or LINEAR_API_KEY_FILE -- same vars bin/estate-twin-runtime uses.
    """
    # Resolve token -- same two-source shape as bin/estate-twin-runtime's _linear_token()
    token = os.environ.get("LINEAR_API_KEY", "").strip()
    if not token:
        path = os.environ.get("LINEAR_API_KEY_FILE", "")
        if path and os.path.exists(path):
            try:
                token = Path(path).read_text(encoding="utf-8").strip()
            except OSError:
                token = ""
    if not token:
        return "LINEAR_API_KEY not configured — cannot reach Cyrus"

    # Parse issue ID from session_id -- the part before the last colon
    issue_id = session_id.rsplit(":", 1)[0]

    comment_body = f"**Steer from FleetView** (by {by}):\n\n{text}"
    query = """
mutation CommentCreate($issueId: String!, $body: String!) {
  commentCreate(input: {issueId: $issueId, body: $body}) {
    success
    comment { id }
  }
}
"""
    variables = {"issueId": issue_id, "body": comment_body}

    if not _LINEAR_API.startswith("https://"):
        return f"refusing a non-https Linear endpoint: {_LINEAR_API}"

    body_bytes = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(  # noqa: S310 - scheme asserted above
        _LINEAR_API,
        data=body_bytes,
        headers={"Authorization": token, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - as above
            out = json.loads(resp.read())
    except Exception as exc:  # noqa: BLE001
        return f"{exc.__class__.__name__}: {exc}"

    if "errors" in out and out.get("data") is None:
        return f"Linear API error: {out['errors'][0].get('message', 'unknown')}"
    data = out.get("data") or {}
    if not (data.get("commentCreate") or {}).get("success"):
        return "Linear commentCreate returned success=false"
    return None


def _dispatch_steer(session_id: str, runtime: str, by: str, text: str) -> str | None:
    """Route the steer to the right runtime's native channel."""
    if runtime == "sovereign":
        return _dispatch_steer_sovereign(session_id, by, text)
    elif runtime == "claude-code":
        return _dispatch_steer_claude_code(session_id, by, text)
    elif runtime == "otto":
        return _dispatch_steer_otto(session_id, by, text)
    elif runtime == "cyrus":
        return _dispatch_steer_cyrus(session_id, by, text)
    else:
        return f"no dispatch path for runtime {runtime!r}"


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

    error = _dispatch_steer(session_id, runtime, by, text)
    return _record(
        session_id, runtime, "steer", by, text, ok=error is None, error=error
    )


def signals_for(session_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """Every signal attempt recorded for a session, newest first -- the audit trail a board row
    can show, mirroring notes_for's read-back in notes.py."""
    session_id = (session_id or "").strip()
    if not session_id:
        return []
    limit = max(1, min(int(limit or 100), 500))
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM fleetview_signals WHERE session_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


# --------------------------------------------------------------------------- reply channel
#
# WHAT THE SESSIONS SAID BACK. A steer has an audit row (`fleetview_signals`); this is the other
# half of a conversation: the session's own output, or a person's, written through one door so the
# board can show a thread instead of two disconnected logs.


def reply(
    session_id: str,
    runtime: str,
    text: str,
    author: str = "agent",
    in_reply_to: int | None = None,
) -> dict[str, Any]:
    """Record what a session said. The write half of the reply channel.

    Deliberately NOT routed through `_require_channel`: a runtime with no steering path can still
    speak. The pi extension, a shell hook, and a person at a keyboard all reach this the same way,
    so a runtime gains a voice the moment it can make one HTTP call -- which is a far lower bar
    than gaining a steering channel.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        raise InvalidSignal("session_id is required")
    text = (text or "").strip()
    if not text:
        raise InvalidSignal("text is required")
    # SCRUB BEFORE STORING, not at render time.
    #
    # An agent's reply routinely quotes a path and can quote a credential it just read; this table
    # is also read by the fleet-wide feed, so a secret caught only in the panel would still be in
    # the database and in every other reader. Redacting at the writer means it never lands at all.
    # See redact.py for what it catches and, honestly, for what it cannot.
    try:
        from fleetview_backend import redact as _redact_mod  # noqa: PLC0415

        text, _removed = _redact_mod.redact(text)
    except Exception:  # noqa: BLE001,S110 -- a missing scrubber must not drop a message
        # Fail OPEN, deliberately, and unlike almost every other guard here: losing a conversation
        # turn is worse than the residual risk of a secret the patterns would have caught, and this
        # is a mitigation rather than a boundary.
        pass
    author = (author or "agent").strip() or "agent"
    # A cap, because this is rendered in a panel and a model that loops must not fill the screen
    # or the disk. 8000 characters is longer than any spoken answer and shorter than a runaway.
    if len(text) > 8000:
        text = text[:8000] + "…"
    runtime = (runtime or "unknown").strip() or "unknown"
    with _connect() as con:
        cur = con.execute(
            "INSERT INTO fleetview_replies "
            "(session_id, runtime, author, text, in_reply_to, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, runtime, author, text, in_reply_to, _now()),
        )
        row = con.execute(
            "SELECT * FROM fleetview_replies WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _reply_to_dict(row)


def replies_for(session_id: str = "", limit: int = 20) -> list[dict[str, Any]]:
    """The newest replies, for one session or for the whole board.

    An empty `session_id` returns the fleet-wide feed -- what was said most recently, by anyone --
    which is what a board needs to show a conversation the reader is not already looking at.
    """
    session_id = (session_id or "").strip()
    limit = max(1, min(int(limit or 20), 200))
    with _connect() as con:
        if session_id:
            rows = con.execute(
                "SELECT * FROM fleetview_replies WHERE session_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM fleetview_replies ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [_reply_to_dict(r) for r in rows]


def _reply_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """A reply row as a plain dict.

    NOT `_row_to_dict`. That one reads `kind`, which only `fleetview_signals` has -- reusing it
    raised `IndexError: No item with that key` on the first read of a reply, which is what a shared
    serializer does when two tables only look similar. A reply has `author` and `in_reply_to`; a
    signal has `kind` and `ok`.
    """
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "runtime": row["runtime"],
        "author": row["author"],
        "text": row["text"],
        "in_reply_to": row["in_reply_to"],
        "created_at": row["created_at"],
    }


# --------------------------------------------------------------------------- work channel
#
# WHAT EACH SESSION IS WORKING ON, one current-state row per session. The Fleet board merges this
# into rows it already renders; a conversation panel shows what was said, this shows what is
# being done right now.


def record_work(
    session_id: str,
    runtime: str,
    branch: str = "",
    step: str = "",
    pid: int | None = None,
) -> dict[str, Any]:
    """Upsert what a session is working on. One row per session -- this is current state, not a log.

    A LOG WOULD BE WRONG HERE. "What is it working on" has exactly one answer at a time, and forty
    historical steps would make the reader choose between them. The step changes are already in
    `session_events`; this table only holds the latest.
    """
    session_id = (session_id or "").strip()
    if not session_id:
        raise InvalidSignal("session_id is required")
    runtime = (runtime or "unknown").strip() or "unknown"
    with _connect() as con:
        # COALESCE-style merge: a call that reports only a step must not blank the branch, and one
        # reporting only a branch must not blank the step. The two arrive from different hooks.
        con.execute(
            "INSERT INTO fleetview_work (session_id, runtime, branch, step, pid, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(session_id) DO UPDATE SET "
            "  runtime = excluded.runtime, "
            "  branch  = CASE WHEN excluded.branch <> '' THEN excluded.branch ELSE branch END, "
            "  step    = CASE WHEN excluded.step   <> '' THEN excluded.step   ELSE step   END, "
            "  pid     = COALESCE(excluded.pid, pid), "
            "  updated_at = excluded.updated_at",
            (
                session_id,
                runtime,
                (branch or "")[:200],
                (step or "")[:200],
                pid,
                _now(),
            ),
        )
        row = con.execute(
            "SELECT * FROM fleetview_work WHERE session_id = ?", (session_id,)
        ).fetchone()
    return dict(row) if row else {}


def work_for() -> dict[str, dict[str, Any]]:
    """Every session's current work, keyed by session id, for the board to merge into its rows."""
    with _connect() as con:
        rows = con.execute("SELECT * FROM fleetview_work").fetchall()
    return {r["session_id"]: dict(r) for r in rows}

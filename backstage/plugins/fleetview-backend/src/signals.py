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
  ESTATE_STATE_PATH_PREFIX -- ledger root, default ~/.claude/state/prompt-ledger/; directives dir
                              is derived as <ledger_root>/../directives/
  NATS_URL             -- default nats://nats.event-bus.svc:4222
  LINEAR_API_KEY       -- Linear API token (or LINEAR_API_KEY_FILE path)
  LINEAR_API_KEY_FILE  -- path to file containing the Linear API token
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
import contextlib
import sqlite3
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_DB_DEFAULT = _ROOT / "catalog" / "estate.db"

MAX_TEXT_LENGTH = 4000

# How stale a reported pid may be before we refuse to signal it. A live session re-reports at every
# turn boundary, so this only ever rejects a record whose process is probably gone -- and because
# pids are reused (this host: kern.maxproc = 2088) a stale number can name something innocent.
PID_MAX_AGE_DEFAULT = 600
PID_MAX_AGE_S = int(os.environ.get("FLEETVIEW_PID_MAX_AGE_S", PID_MAX_AGE_DEFAULT))
DEFAULT_NUDGE_TEXT = "Nudge from FleetView: this session has been idle. Please post a status, or wrap up."

_LINEAR_API = "https://api.linear.app/graphql"

_SUPPORTED_RUNTIMES = frozenset({"sovereign", "claude-code", "otto", "cyrus", "pi"})

# Which runtimes each signal actually has a delivery path for. Measured 2026-09-18 from the
# client's own backend log -- this is the table that was implicit and wrong before:
#
#   POST /nudge          200  (claude-code)
#   POST /approve        502  <-- should have been 422
#   POST /deny           502  <-- should have been 422
#   POST /stop           404, then 500  <-- 404 was a stale route; the 500 was sovereign
#
# WHY THIS IS A TABLE AND NOT THREE `else` CLAUSES. An `else: error = f"... not yet wired"`
# recorded a FAILED ATTEMPT and returned it through the `ok is None` path, so routes.py turned
# it into 502 -- "the signal was attempted against a real session and failed". That is false:
# nothing was attempted, because there is no channel. 502 tells an operator the far end is sick
# and sends them to debug a service that is fine; 422 says the request named a combination that
# does not exist, which is true and actionable.
#
# `steer` covers all four (CP8). `stop` covers the two runtimes with a readable pause point.
# approve/deny cover `sovereign` alone, and that is a statement about the estate, not a TODO:
# the other three take direction mid-turn through the same channel as steer, so an approve is
# a steer whose text says approve, and it is already expressible. A separate verb would be a
# second code path to the same place.
SIGNAL_RUNTIMES: dict[str, frozenset[str]] = {
    "steer": frozenset({"sovereign", "claude-code", "otto", "cyrus", "pi"}),
    "stop": frozenset({"sovereign", "claude-code", "pi"}),
    "approve": frozenset({"sovereign"}),
    "deny": frozenset({"sovereign"}),
    # `kill` HAS A CHANNEL ONLY WHERE A PID IS REPORTED, which today means the runtimes whose
    # extension posts to /work. It skipped this table entirely -- every other verb consults it, and
    # `kill` validating only that its fields were non-empty meant it would attempt a signal for any
    # runtime a caller named. The table is the one place that decides which verb reaches which
    # runtime, and a destructive verb is the last one that should bypass it.
    "kill": frozenset({"pi", "claude-code"}),
}


class InvalidSignal(ValueError):
    """Raised for a request that never touched a real session -- routes.py turns this into 400."""


class UnsupportedRuntime(ValueError):
    """Raised for a runtime with no live signal path -- routes.py turns this into 422."""


def _db_path() -> Path:
    return Path(os.environ.get("ESTATE_DB", str(_DB_DEFAULT)))


# Schemas created this process, keyed by database path.
#
# WHY THIS EXISTS. Every read and write ran `CREATE TABLE IF NOT EXISTS` -- eight call sites, on a
# route the board polls every 2 seconds. Individually cheap, collectively not: each takes a write
# lock on the file, and two processes share this database (the backend and the voice service), so
# that is lock traffic competing with the reads the board needs.
#
# Once per process is the right granularity: the schema cannot change while a process runs, and a
# restart re-checks, which is exactly when a migration could have happened.
_SCHEMA_READY: set[str] = set()

# The three tables, exactly as they exist in `catalog/estate.db`.
#
# WRITTEN OUT IN FULL RATHER THAN DERIVED, because these ARE the schema -- a dump of the live
# database is authoritative in a way that a summary would not be. `read_at` and `pid` are appended
# style because that is how they arrived (additive migrations), and keeping the shapes identical
# means a database created here is indistinguishable from one migrated in place.
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
    # first -- which is exactly how the missing signals table survived testing.
    try:
        _ensure_schema(con)
    except sqlite3.Error:
        raise
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
    `read_at` describes the READ (did the agent see it). Measured 2026-09-18, before this field:

        id 21  claude-code:...  deny  ok=0  (no read_at column existed)
        id 18  claude-code:...  steer ok=1  -- the board rendered this as 'steered'

    The `ok=1` row meant "a file was written to ~/.claude/state/directives/", and nothing read
    that file for a day. `read_at` is what makes "delivered" and "received" tellable apart.

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


def _require_channel(signal: str, runtime: str, session_id: str) -> None:
    """Refuse a signal this runtime has no channel for, as UnsupportedRuntime (-> 422).

    Raised BEFORE any dispatch is attempted and before any audit row is written, for the same
    reason `notes.py`'s InvalidNote leaves no row: an attempt that never reached a session is
    not an attempt, and recording it as one is what made these buttons look like failures.
    """
    if runtime not in _SUPPORTED_RUNTIMES:
        raise UnsupportedRuntime(f"{runtime} has no live signal path yet")
    if runtime not in SIGNAL_RUNTIMES[signal]:
        supported = ", ".join(sorted(SIGNAL_RUNTIMES[signal]))
        raise UnsupportedRuntime(
            f"{signal} has no channel for {runtime} (session {session_id}); "
            f"it is wired for {supported}. For this runtime, send the instruction as a steer."
        )


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


def _dispatch_steer_pi(session_id: str, by: str, text: str) -> str | None:
    """Write the steer to ~/.claude/state/directives/<raw_uuid>.json -- the same mailbox
    `_dispatch_steer_claude_code` uses, deliberately.

    WHY THE SAME FILE AND NOT A NEW TRANSPORT. LAW 43: no second gauntlet, no second transport.
    The mailbox exists, carries real traffic, and its protocol (write `<uuid>.json`, the session
    renames it `.consumed`) is already proven by claude-code. The pi extension
    (`~/.pi/agent/extensions/fleetview-directives.ts`) is the receiving half, reading the same
    directory at session_start and turn_start.

    Without that extension installed the file is written and never read -- so this dispatcher
    checks for it first and refuses honestly with the reason, rather than reporting a `200` for a
    steer no one will ever see. "Succeeded" must mean delivered or deliverable.

    Delivery is next-turn for a session already running (the extension drains at turn_start); a
    session that is NOT running picks it up at its next session_start. Both are real delivery;
    mid-inference interruption of a pi session is not possible from here and is not claimed.

    CONFIG (LAW 46): ESTATE_STATE_PATH_PREFIX -- ledger root, default
    ~/.claude/state/prompt-ledger/; directives dir is <ledger_root>/../directives/, matching
    _dispatch_steer_claude_code exactly.
    """
    # The receiving extension, or the file is a dead letter. Checked here, before the write, so
    # the caller gets a 502 with an actionable reason instead of a false success.
    ext = Path.home() / ".pi" / "agent" / "extensions" / "fleetview-directives.ts"
    if not ext.is_file():
        return (
            "pi steering is not deliverable on this machine: the receiving extension "
            f"{ext} is not installed, so a written directive would never be read"
        )

    raw_uuid = session_id.rsplit(":", 1)[-1]
    ledger_root = Path(
        os.environ.get(
            "ESTATE_STATE_PATH_PREFIX",
            os.path.expanduser("~/.claude/state/prompt-ledger/"),
        )
    )
    directives_dir = ledger_root.parent / "directives"

    try:
        os.makedirs(directives_dir, exist_ok=True)
        dest = directives_dir / f"{raw_uuid}.json"
        # A consumed marker from a previous steer must not shadow this one: the extension claims
        # by renaming to `.consumed`, and a stale marker beside a fresh `.json` is harmless, but
        # leaving the old `.json` in place would deliver the OLD text again.
        if dest.exists():
            dest.unlink()
        dest.write_text(
            json.dumps(
                {"session_id": session_id, "by": by, "text": text, "written_at": _now()}
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        return f"OSError writing pi directive: {exc}"
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
    elif runtime == "pi":
        return _dispatch_steer_pi(session_id, by, text)
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
    # steer has a channel for all four runtimes, so this is equivalent to the old membership
    # check -- but it goes through the same table, so the four signals cannot drift apart.
    _require_channel("steer", runtime, session_id)

    error = _dispatch_steer(session_id, runtime, by, text)
    return _record(
        session_id, runtime, "steer", by, text, ok=error is None, error=error
    )


def stop(session_id: str, runtime: str, by: str) -> dict[str, Any]:
    session_id = (session_id or "").strip()
    runtime = (runtime or "").strip()
    by = (by or "").strip()
    if not session_id:
        raise InvalidSignal("session_id is required")
    if not runtime:
        raise InvalidSignal("runtime is required")
    if not by:
        raise InvalidSignal("by is required")
    _require_channel("stop", runtime, session_id)
    if runtime == "pi":
        # A MARKER FILE, not a mailbox message.
        #
        # `steer` writes a directive that is claimed ONCE and renamed `.consumed` -- right for a
        # message, wrong for a stop: the extension re-checks at every turn boundary and a consumed
        # file would answer "no" the second time. The marker stays, so the answer stays yes.
        #
        # WHAT ACTUALLY STOPS is `ctx.shutdown()` in the extension, at the next turn boundary. It is
        # the runtime's own graceful exit, so `session_shutdown` fires and the session file closes
        # cleanly -- unlike a SIGKILL, which would discard in-flight work and leave the record mid
        # tool call. A session that is wedged and never reaches a boundary is therefore NOT killed
        # by this, and the board says so rather than pretending.
        import pathlib  # noqa: PLC0415

        raw = session_id.rsplit(":", 1)[-1]
        ledger = os.environ.get(
            "ESTATE_STATE_PATH_PREFIX",
            os.path.expanduser("~/.claude/state/prompt-ledger/"),
        )
        d = pathlib.Path(ledger).parent / "directives"
        try:
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{raw}.stop").write_text(
                json.dumps({"session_id": session_id, "by": by, "at": _now()}),
                encoding="utf-8",
            )
            error = None
        except OSError as exc:
            error = f"OSError writing stop marker: {exc}"
    elif runtime == "sovereign":
        try:
            from sovereign.engine import client as ec

            result = asyncio.run(ec.signal(session_id, "stop", by, ""))
            error = None if result.get("ok") else str(result.get("error") or "rejected")
        except ImportError as exc:
            # The engine package is absent on this machine. A 502 here says 'the far end is
            # sick', which is false -- the channel exists and this host cannot open it.
            error = f"sovereign engine not importable here: {exc}"
        except Exception as exc:  # noqa: BLE001 - a dead workflow is a fact to report, not hide
            error = f"{exc.__class__.__name__}: {exc}"
    elif runtime == "claude-code":
        raw = session_id.rsplit(":", 1)[-1]
        dr = (
            Path(
                os.environ.get(
                    "ESTATE_STATE_PATH_PREFIX",
                    os.path.expanduser("~/.claude/state/prompt-ledger/"),
                )
            ).parent
            / "directives"
        )
        try:
            os.makedirs(dr, exist_ok=True)
            (dr / f"{raw}.json").write_text(
                json.dumps(
                    {
                        "session_id": session_id,
                        "by": by,
                        "kind": "stop",
                        "written_at": _now(),
                    }
                )
            )
            error = None
        except OSError as exc:
            error = str(exc)
    else:  # unreachable: _require_channel already refused anything not named above
        raise UnsupportedRuntime(f"stop has no channel for {runtime}")
    return _record(session_id, runtime, "stop", by, "", ok=error is None, error=error)


def approve(session_id: str, runtime: str, by: str, text: str = "") -> dict[str, Any]:
    session_id = (session_id or "").strip()
    runtime = (runtime or "").strip()
    by = (by or "").strip()
    text = (text or "").strip()
    if not session_id:
        raise InvalidSignal("session_id is required")
    if not runtime:
        raise InvalidSignal("runtime is required")
    if not by:
        raise InvalidSignal("by is required")
    _require_channel("approve", runtime, session_id)
    if runtime == "sovereign":
        try:
            from sovereign.engine import client as ec

            result = asyncio.run(ec.signal(session_id, "approve", by, text))
            error = None if result.get("ok") else str(result.get("error") or "rejected")
        except ImportError as exc:
            error = f"sovereign engine not importable here: {exc}"
        except Exception as exc:  # noqa: BLE001
            error = f"{exc.__class__.__name__}: {exc}"
    else:  # unreachable: _require_channel refused anything else
        raise UnsupportedRuntime(f"approve has no channel for {runtime}")
    return _record(
        session_id, runtime, "approve", by, text, ok=error is None, error=error
    )


def deny(session_id: str, runtime: str, by: str, text: str = "") -> dict[str, Any]:
    session_id = (session_id or "").strip()
    runtime = (runtime or "").strip()
    by = (by or "").strip()
    text = (text or "").strip()
    if not session_id:
        raise InvalidSignal("session_id is required")
    if not runtime:
        raise InvalidSignal("runtime is required")
    if not by:
        raise InvalidSignal("by is required")
    _require_channel("deny", runtime, session_id)
    if runtime == "sovereign":
        try:
            from sovereign.engine import client as ec

            result = asyncio.run(ec.signal(session_id, "deny", by, text))
            error = None if result.get("ok") else str(result.get("error") or "rejected")
        except ImportError as exc:
            error = f"sovereign engine not importable here: {exc}"
        except Exception as exc:  # noqa: BLE001
            error = f"{exc.__class__.__name__}: {exc}"
    else:  # unreachable: _require_channel refused anything else
        raise UnsupportedRuntime(f"deny has no channel for {runtime}")
    return _record(session_id, runtime, "deny", by, text, ok=error is None, error=error)


def signals_for(session_id: str, limit: int = 100) -> list[dict[str, Any]]:
    """A session's recent signal attempts, newest first -- the audit trail a board row can show.

    LIMITED, AND THAT IS THE FIX. This returned EVERY row ever recorded for a session, and the
    board fetches it on its 2-second poll -- so a session that had been steered a few hundred times
    sent a few hundred rows every two seconds, for ever, to render at most a handful. The reply
    table was already capped at 200; this one grew without bound because its read had no LIMIT.

    100 is above any conversation a person will scroll and below anything that costs a poll.
    """
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
    # See src/redact.py for what it catches and, honestly, for what it cannot.
    try:
        import importlib.util as _ilu  # noqa: PLC0415

        _spec = _ilu.spec_from_file_location(
            "fleetview_redact", Path(__file__).resolve().parent / "redact.py"
        )
        _redact_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_redact_mod)
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


# --------------------------------------------------------------------------- hard kill
#
# SIGTERM, FOR THE ROGUE CASE.
#
# `stop` is a marker the session reads at its next turn boundary -- correct and safe, and useless
# against an agent that is looping, spending, or wedged inside a provider call, because there is no
# next turn. This is the other end: the process itself, addressed by the PID the extension reports
# via /work.
#
# WHY THIS IS ACCEPTABLE HERE. Nothing durable is lost. The work is on the filesystem: every edit is
# written, the session file holds the transcript, and the branch holds the state. A hard kill costs
# the IN-FLIGHT TURN and nothing else, which is why the founder asked for both: "we need both in
# case of rogue agent and we need to be able to also salvage the work, but it is in the filesystem
# anyway".
#
# SIGTERM BEFORE SIGKILL, deliberately. SIGTERM is catchable, so a session that has the chance runs
# its shutdown hooks; SIGKILL is sent only if asked, because a process that ignores SIGTERM is
# usually one doing something worth a moment's grace.


def _pid_for(session_id: str) -> tuple[int | None, str]:
    """The PID a session last reported, WITH A FRESHNESS CHECK. Returns (pid, reason-if-refused).

    WHY THIS IS NOT JUST A SELECT.

    `os.kill(pid)` signals a NUMBER. Between the moment a session reports its pid and the moment
    somebody presses kill, that process may have exited and its number been handed to something
    else -- and this machine's pid space is `kern.maxproc = 2088`, measured 2026-09-20, so reuse
    takes seconds, not months. A stale row therefore does not name a dead session, it names an
    arbitrary process: the board's own backend, an editor, in principle anything this user may
    signal.

    THREE GUARDS, each cheap, because the cost of being wrong is SIGKILL against an innocent
    process:

      1. FRESHNESS. A pid older than PID_MAX_AGE_S is refused. A session that is alive reports its
         pid at every turn boundary, so a current session always has a recent one; a row that has
         not been touched in ten minutes is a record of a process that may no longer exist.
      2. LIVENESS. `os.kill(pid, 0)` sends no signal and answers "does this process exist" -- FreeBSD
         and Linux both raise ESRCH for a dead pid and EPERM for one this user may not touch. EPERM
         is treated as ALIVE (the process exists) and left for the real signal to report.
      3. IDENTITY. Where the platform allows reading it, the process's command line must contain
         `pi` or `node` -- the runtimes this board steers. This is the guard that actually catches a
         REUSED pid: a fresh, live, unrelated process passes (1) and (2) and fails this.

    What this deliberately does NOT do is verify the process is THE session, which would need a
    session marker in the environment -- worth adding, and recorded here as a known gap rather than
    implied to be covered.
    """
    import time as _time  # noqa: PLC0415

    with _connect() as con:
        row = con.execute(
            "SELECT pid, updated_at FROM fleetview_work WHERE session_id = ?",
            (session_id,),
        ).fetchone()
    if not row or row["pid"] is None:
        return None, "no PID reported for this session"

    pid = int(row["pid"])

    # 1. Freshness.
    age = None
    try:
        stamp = dt.datetime.fromisoformat(str(row["updated_at"]).replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
        age = _time.time() - stamp.timestamp()
    except (ValueError, TypeError):
        return None, f"cannot read the age of pid {pid}; refusing to signal it"
    if age is None or age > PID_MAX_AGE_S:
        return None, (
            f"pid {pid} was reported {int(age or 0)}s ago (limit {PID_MAX_AGE_S}s) -- too old to "
            f"signal safely, because the number may have been reused"
        )

    # 2. Liveness. Signal 0 delivers nothing.
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None, f"process {pid} no longer exists"
    except PermissionError:
        # It exists; this user simply may not signal it. That is for the real signal to report.
        pass
    except OSError as exc:
        return None, f"cannot check pid {pid}: {exc.__class__.__name__}"

    # 3. Identity, where the platform exposes it.
    expected = ("pi", "node")
    try:
        proc = subprocess.run(  # noqa: S603 -- argv list, no shell; the estate's tool-invocation idiom
            ["ps", "-o", "command=", "-p", str(pid)],  # noqa: S607 -- partial path is deliberate -- the tool is resolved from the operator's PATH
            capture_output=True,
            text=True,
            timeout=5,
        )
        cmdline = (proc.stdout or "").strip()
        if cmdline and not any(e in cmdline.lower() for e in expected):
            return None, (
                f"pid {pid} is not a pi or node process (it is {cmdline[:60]!r}) -- refusing, "
                f"because this pid was probably reused"
            )
    except (OSError, subprocess.SubprocessError):
        # `ps` unavailable or slow: guards 1 and 2 already ran, and refusing on a missing `ps`
        # would break kill on a host that simply lacks it.
        pass

    return pid, ""


def kill(session_id: str, runtime: str, by: str, force: bool = False) -> dict[str, Any]:
    """SIGTERM (or SIGKILL) the session's process. Records the attempt either way."""
    session_id = (session_id or "").strip()
    runtime = (runtime or "").strip()
    by = (by or "").strip()
    if not session_id:
        raise InvalidSignal("session_id is required")
    if not runtime:
        raise InvalidSignal("runtime is required")
    if not by:
        raise InvalidSignal("by is required")
    # The same channel table every other verb uses. See SIGNAL_RUNTIMES: `kill` was the one verb
    # that skipped it.
    _require_channel("kill", runtime, session_id)

    pid, refusal = _pid_for(session_id)
    if pid is None:
        # NOT a failure of the button: the session never reported a PID, or the one it reported
        # cannot be safely signalled. The reason is the useful part -- "no PID" and "that PID is
        # now some other program" are different facts and both are actionable.
        return _record(
            session_id,
            runtime,
            "kill",
            by,
            "",
            ok=False,
            error=refusal or "no PID reported for this session",
        )

    import signal as _signal  # noqa: PLC0415

    sig = _signal.SIGKILL if force else _signal.SIGTERM
    try:
        os.kill(pid, sig)
        error = None
    except ProcessLookupError:
        error = f"process {pid} is already gone"
    except PermissionError:
        error = f"not permitted to signal process {pid}"
    except OSError as exc:
        error = f"{exc.__class__.__name__}: {exc}"
    row = _record(
        session_id, runtime, "kill", by, f"pid {pid}", ok=error is None, error=error
    )
    row["pid"] = pid
    return row

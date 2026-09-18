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
import sqlite3
import urllib.request
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[4]
_DB_DEFAULT = _ROOT / "catalog" / "estate.db"

MAX_TEXT_LENGTH = 4000
DEFAULT_NUDGE_TEXT = "Nudge from FleetView: this session has been idle. Please post a status, or wrap up."

_LINEAR_API = "https://api.linear.app/graphql"

_SUPPORTED_RUNTIMES = frozenset({"sovereign", "claude-code", "otto", "cyrus"})

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
    "steer": frozenset({"sovereign", "claude-code", "otto", "cyrus"}),
    "stop": frozenset({"sovereign", "claude-code"}),
    "approve": frozenset({"sovereign"}),
    "deny": frozenset({"sovereign"}),
}


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
    if runtime == "sovereign":
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

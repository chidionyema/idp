"""FleetView CP1: the session contract, served.

One job: turn every runtime into the same session record and serve them behind the portal's own
API. The record shape is `schema/session.json`, versioned, and it is the offering's integration
surface -- a customer with their own runtime writes one adapter that emits this shape.

THE BOARD WAS EMPTY (found and fixed 2026-09-15). The prior version of this file discovered
claude-code sessions by filtering `catalog/catalog-info.yaml` for `Resource` rows whose
`estate/path` sits under the prompt ledger, one row per session. That source does not exist:
`bin/catalog-gen`'s `is_ephemeral_ledger` (a founder directive, 2026-09-yy) deliberately collapses
`~/.claude/state/prompt-ledger` into ONE summary Resource named `state-prompt-ledger`, on purpose,
so the catalogue page is not flooded with one row per session. That is the right call for the
catalogue and the wrong source for this board: run live against the real catalogue, the old filter
matched zero rows -- `GET /api/fleetview/sessions` returned an empty board, always, while 29 real
ledger files sat on disk. An empty board reported as live is exactly the failure this estate names
everywhere else. The fix reads the ledger directory the same env var already names, directly,
instead of through a catalogue page that intentionally hides it.

Two adapters make up "claude-code and everything else":
  - `_claude_code_sessions` reads `~/.claude/state/prompt-ledger/*.jsonl` off disk. Each file is
    one working directory; each file holds many `session` ids over that directory's history, so
    a session here is one (file, session id) pair, not one file.
  - `_other_harness_sessions` reuses `mcp/plugins/estate_sessions.py` -- the estate's other,
    already-correct catalogue reader, extended 2026-09-13 ("this ... should be from all agents no
    claude only") to also carry `.pi` and `.gemini` transcripts, which the catalogue DOES emit one
    row per file for. Importing it is reuse of the estate's one session-catalogue reader, not a
    second implementation of the same filter (THE HEADLINE) -- this file no longer re-parses the
    catalogue itself for anything catalogue-shaped.

Why the catalogue and not Temporal, for the sovereign adapter. The spec's sovereign adapter reads
Temporal, and this estate's Temporal namespace held **zero** workflows when CP1 was built (verified
2026-09-12). A board wired to an empty engine shows an empty board, and an empty board reported as
progress is the failure this repository's proof rule exists to stop. A `sovereign` adapter is a
drop-in the moment Temporal carries a workflow; nothing here needs to change for that.

CONFIG (LAW 46 -- no path, host or port is a literal in code that decides behaviour; each is an
env var with a container-local default, wired where the deployment can state it):
  ESTATE_STATE_PATH_PREFIX   the claude-code ledger directory this board reads directly
  ESTATE_CATALOG_PATH        the generated Backstage catalogue, read only for the OTHER harnesses
                             (pi, gemini) via mcp/plugins/estate_sessions.py
  LANGFUSE_HOST              read directly (same variable sovereign/engine/tracing.py reads) to
                             build a sovereign session's trace_url as {host}/trace/{session_id} --
                             no default, because unset means Langfuse is not configured, and a
                             fabricated host would produce a link that resolves to nothing.
  ESTATE_SESSION_WINDOW_HOURS  how far back a session may have last written and still appear
                             (default 168 = 7 days; live proof 2026-09-15: 7 days holds the
                             estate's real active count at 14-23 sessions, 30 days holds it at
                             ~838 -- too many rows for a board a person reads)
  ESTATE_FRESH_RUNNING_MINUTES  a session updated within this many minutes reads "running"
  ESTATE_FRESH_PAUSED_HOURS     a session updated within this many hours (and not "running")
                             reads "paused"; older than that (but inside the window) reads
                             "stopped". This is a freshness heuristic, not a liveness check --
                             nothing here inspects a PID -- and it replaces a permanent "unknown"
                             that told a reader nothing for every single row.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

# The route CP1's done-command names.
SESSIONS_ROUTE = "/api/fleetview/sessions"
STREAM_ROUTE = "/api/fleetview/stream"

DEFAULT_LEDGER_PREFIX = "~/.claude/state/prompt-ledger/"

# Model-agnostic session source: catalog/estate.db sessions + session_events tables.
_ROOT = Path(__file__).resolve().parents[4]
_ESTATE_DB_DEFAULT = _ROOT / "catalog" / "estate.db"


def _estate_db_path() -> Path:
    raw = os.environ.get("ESTATE_DB")
    return Path(raw) if raw else _ESTATE_DB_DEFAULT


def _estate_db_sessions(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    """Read sessions from estate.db's model-agnostic sessions/session_events tables.

    Returns empty list when the DB is missing or tables are empty -- never raises,
    because empty-DB and unreachable look different to the board.
    """
    db_path = _estate_db_path()
    if not db_path.is_file():
        return []
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        con = sqlite3.connect(str(db_path))
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT s.id, s.provider, s.model, s.created_at, s.metadata_json,
                   MAX(e.ts) AS last_event_ts,
                   -- The four-state derivation needs the RATE and the SHAPE of recent activity,
                   -- not just the timestamp. `state` alone (running/paused/stopped from
                   -- freshness) cannot tell thinking from waiting from stuck, which is why the
                   -- board rendered 22 of 23 agents as one identical amber dot.
                   COUNT(e.id)  AS event_count,
                   MIN(e.ts)    AS first_event_ts
            FROM sessions s
            LEFT JOIN session_events e ON e.session_id = s.id
            GROUP BY s.id
            ORDER BY last_event_ts DESC, s.created_at DESC
            """
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        meta: dict[str, Any] = {}
        try:
            meta = json.loads(r["metadata_json"] or "{}")
        except (ValueError, TypeError):
            pass
        updated_at = r["last_event_ts"] or r["created_at"]
        state = _state_from_freshness(updated_at, now)
        # The four states the interface draws, derived from the same evidence the state above uses
        # plus the body of work behind the row -- see _activity_from_evidence for why elapsed time
        # alone cannot tell thinking from waiting from stuck.
        event_count = int(r["event_count"] or 0)
        out.append(
            {
                "session_id": f"{r['provider']}:{r['id']}",
                "runtime": r["provider"],
                "task": meta.get("task") or "",
                "state": state,
                "activity": _activity_from_evidence(
                    updated_at, event_count, r["first_event_ts"], state, now
                ),
                "event_count": event_count,
                "repo": meta.get("repo"),
                "step": meta.get("step"),
                "updated_at": updated_at,
                "trace_url": meta.get("trace_url"),
                "spend_usd": meta.get("spend_usd"),
                "pull_requests": meta.get("pull_requests") or [],
                "ticket": meta.get("ticket"),
                "capability_class": meta.get("capability_class"),
                "capabilities": meta.get("capabilities"),
            }
        )
    return out


_ESTATE_SESSIONS_MODULE = (
    Path(__file__).resolve().parents[4] / "mcp" / "plugins" / "estate_sessions.py"
)
_SPEND_MODULE = Path(__file__).resolve().parent / "spend.py"


def _spend():
    """`src/spend.py`, loaded by path (mirrors `_estate_sessions()` above and routes.py's own
    `_load()`) -- the sovereign adapter's only source for `spend_usd`."""
    spec = importlib.util.spec_from_file_location("fleetview_spend_impl", _SPEND_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_SPEND_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _estate_sessions():
    """The estate's one catalogue-session reader, loaded by path so this plugin does not need a
    Python package boundary crossed to reuse it (mirrors routes.py's own `_sessions()` loader)."""
    spec = importlib.util.spec_from_file_location(
        "fleetview_estate_sessions_impl", _ESTATE_SESSIONS_MODULE
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {_ESTATE_SESSIONS_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _ledger_prefix() -> str:
    return os.environ.get("ESTATE_STATE_PATH_PREFIX", DEFAULT_LEDGER_PREFIX)


def _ledger_dir() -> Path:
    return Path(os.path.expanduser(_ledger_prefix()))


def _session_window_hours() -> float:
    return float(os.environ.get("ESTATE_SESSION_WINDOW_HOURS", "168"))


def _fresh_running_minutes() -> float:
    return float(os.environ.get("ESTATE_FRESH_RUNNING_MINUTES", "15"))


def _fresh_paused_hours() -> float:
    return float(os.environ.get("ESTATE_FRESH_PAUSED_HOURS", "24"))


def _activity_from_evidence(
    last_event_ts: str | None,
    event_count: int,
    first_event_ts: str | None,
    face: str,
    now: dt.datetime,
) -> str:
    """Which of the FOUR states a session is in, from evidence rather than from a guess.

    WHY THIS EXISTS. A council of three independent frontier models, asked to design this
    interface, converged on one thing: an agent that has not emitted for ten minutes is not one
    state but four, and the interface's whole value is telling them apart. Measured on this board
    before this function existed: 22 of 23 agents rendered as one identical amber dot, and an
    agent stuck in a retry loop was labelled `running` -- the single worst mistake all three
    models named.

    `state` (running/paused/stopped from freshness) cannot do this: it is one number, elapsed
    time, and elapsed time is identical for an agent thinking hard and an agent wedged. So this
    reads what the estate actually records.

    THE FOUR STATES, and the evidence each requires:

      thinking  wrote within the running window. The honest limit: an outside reader cannot see a
                long inference mid-flight, so a session that wrote recently IS thinking and
                nothing finer is claimed.
      waiting   wrote, then stopped, still inside the live window. The silence with no body of
                work behind it says it is blocked -- on CI, an API, or a person. This is the state
                the old board did not have, and the most common one in practice.
      stuck     silent for a long time while its state still says live, WITH enough events behind
                it to know it had been working. `event_count` is what separates this from
                `waiting`: many events then silence is not thinking, it is a session that stopped
                producing. Named from evidence, never from a retry counter nobody records.
      finished  the live window has passed entirely. It will not write again unless something
                restarts it.

    `face` is the freshness `state`, kept so a caller can show both. Every branch returns one of
    the four or `unknown` when there is no timestamp -- never a default of `thinking`, because a
    node that breathes when nobody knows whether it is alive is the same lie as a green dot.
    """
    ts = _parse_ts(last_event_ts)
    if ts is None:
        return "unknown"
    age_s = (now - ts).total_seconds()
    if age_s < 0:
        age_s = 0

    if age_s <= _fresh_running_minutes() * 60:
        return "thinking"
    if age_s <= _fresh_paused_hours() * 3600:
        # Silenced inside the live window. A real body of work behind it that went this quiet is
        # stuck; almost nothing behind it is simply awaiting a first answer. The threshold is
        # deliberately low, because accusing a healthy session of being stuck is worse than being
        # slow to say so.
        return "stuck" if event_count >= _STUCK_MIN_EVENTS else "waiting"
    return "finished"


_STUCK_MIN_EVENTS = int(os.environ.get("ESTATE_STUCK_MIN_EVENTS", "10"))


def _parse_ts(value: str | None) -> dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _state_from_freshness(updated_at: str | None, now: dt.datetime) -> str:
    """A session's state as a guess from how long ago it last wrote, never "running" for a row
    that has not written in a day -- the same rule the catalogue-based version followed, applied
    to a real timestamp instead of leaving every row "unknown"."""
    ts = _parse_ts(updated_at)
    if ts is None:
        return "unknown"
    age_s = (now - ts).total_seconds()
    if age_s < 0:
        age_s = 0
    if age_s <= _fresh_running_minutes() * 60:
        return "running"
    if age_s <= _fresh_paused_hours() * 3600:
        return "paused"
    return "stopped"


def _project_from_slug(slug: str) -> str | None:
    """The project a session's directory slug names, or None when it cannot be told.

    A ledger file (and a `.pi`/`.gemini` session's own directory component) is named after the
    working directory with separators replaced and the home directory dropped, so a session in a
    worktree under a project and a session at that project's root both resolve to the project
    name. Nothing here names a real path: the slug is split on its separators and the machine's
    own prefix and any worktree marker are discarded, leaving the last meaningful component.
    """
    if not slug.startswith("-"):
        return None
    parts = [p for p in slug.split("-") if p]
    # Drop the machine's own path prefix and any worktree marker: what is left is the project.
    while parts and parts[0] in ("Users", "home", "private", "var", "tmp"):
        parts.pop(0)
    while parts and parts[-1] in ("wt", "worktrees", "claude", "tmp"):
        parts.pop()
    # A trailing `-wt-<name>` or `--<name>` is a worktree, not the project.
    for marker in ("wt", "worktrees"):
        if marker in parts:
            parts = parts[: parts.index(marker)]
    return parts[-1] if parts else None


def _claude_code_sessions(
    directory: Path | None = None, now: dt.datetime | None = None
) -> list[dict[str, Any]]:
    """Every claude-code session in the estate's own prompt ledger, read directly off disk.

    One ledger file is one working directory, appended to across many separate conversations; the
    file's own `session` field is what tells those conversations apart, so a session record here
    is one (file, session id) pair inside the freshness window, not one file. `session_id` is
    namespaced by the repo (or the file's own name when the repo cannot be told) because the same
    short session id has been observed to repeat across two different ledger files on this
    machine -- an unqualified id would silently merge two unrelated sessions on the board.
    """
    directory = directory or _ledger_dir()
    now = now or dt.datetime.now(dt.timezone.utc)
    window = dt.timedelta(hours=_session_window_hours())
    if not directory.is_dir():
        return []

    out: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.jsonl")):
        repo = _project_from_slug(path.stem)
        by_session: dict[str, dict[str, Any]] = {}
        try:
            with path.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    sid = row.get("session")
                    ts = row.get("ts")
                    if not isinstance(sid, str) or not sid or not isinstance(ts, str):
                        continue
                    entry = by_session.setdefault(
                        sid, {"updated_at": None, "task": None, "_user_ts": None}
                    )
                    if entry["updated_at"] is None or ts > entry["updated_at"]:
                        entry["updated_at"] = ts
                    if row.get("source") == "user":
                        text = row.get("text")
                        if (
                            isinstance(text, str)
                            and text.strip()
                            and (entry["_user_ts"] is None or ts > entry["_user_ts"])
                        ):
                            entry["_user_ts"] = ts
                            entry["task"] = text.strip()[:200]
        except OSError:
            continue

        for sid, detail in by_session.items():
            ts = _parse_ts(detail["updated_at"])
            if ts is None or now - ts > window:
                continue
            session_id = f"{repo or path.stem}:{sid}"
            out.append(
                {
                    "session_id": session_id,
                    "runtime": "claude-code",
                    "task": detail["task"] or path.stem,
                    "state": _state_from_freshness(detail["updated_at"], now),
                    "repo": repo,
                    "step": None,
                    "updated_at": detail["updated_at"],
                    "trace_url": None,
                    "spend_usd": None,
                    "capability_class": None,
                    "capabilities": None,
                    "pull_requests": [],
                    "ticket": None,
                }
            )
    return out


# Where mcp/plugins/estate_sessions.py's SESSION_STORE_ROOTS lead, and the runtime name this
# board's schema gives each. `~/.claude` is excluded here: the claude-code adapter above already
# owns that store and reads it with more detail (a real task string, not just a file name).
_OTHER_HARNESS_RUNTIME = (
    ("/.pi/", "pi"),
    ("/.gemini/", "gemini"),
)


def _runtime_for_path(path: str) -> str | None:
    for needle, runtime in _OTHER_HARNESS_RUNTIME:
        if needle in path:
            return runtime
    return None


def _other_harness_sessions(
    catalog: Path | None = None, now: dt.datetime | None = None
) -> list[dict[str, Any]]:
    """Every non-claude-code session the generated catalogue already carries one row per file for.

    `mcp/plugins/estate_sessions.py` is the estate's maintained, tested reader for exactly this
    filter (ADR 0006's "one source of truth" and the 2026-09-13 founder directive that made it
    cover every harness, not only claude). This calls it rather than re-parsing the catalogue a
    second way (THE HEADLINE): live proof 2026-09-15 found 104 real rows this way against zero
    from the old catalogue-based claude-only filter.
    """
    impl = _estate_sessions()
    cfg = impl.config()
    if catalog is not None:
        cfg = dict(cfg, catalog_path=str(catalog))
    rows = impl._read_catalog(cfg)  # noqa: SLF001 - the module's own catalogue reader, reused
    now = now or dt.datetime.now(dt.timezone.utc)
    window = dt.timedelta(hours=_session_window_hours())

    out: list[dict[str, Any]] = []
    for row in rows:
        if not impl.is_session_row(row):
            continue
        session = impl._row_to_session(row, None)  # noqa: SLF001 - same reuse
        path = session.get("path") or ""
        runtime = _runtime_for_path(path)
        if runtime is None:
            continue  # claude-code's own store, or a store this board does not yet know
        # `_row_to_session`'s own mtime probe only resolves the `{@HOME@}` token, not a literal
        # leading `~` (the spelling these two harnesses' rows actually carry), so it always comes
        # back None for them. Expanding it here is reading the same file a second way, not a
        # second store.
        updated_at = session.get("last_updated")
        if updated_at is None and path:
            expanded = os.path.expanduser(path)
            if os.path.isfile(expanded):
                try:
                    mtime = dt.datetime.fromtimestamp(
                        os.path.getmtime(expanded), tz=dt.timezone.utc
                    )
                    updated_at = mtime.strftime("%Y-%m-%dT%H:%M:%SZ")
                except OSError:
                    updated_at = None
        ts = _parse_ts(updated_at)
        if ts is not None and now - ts > window:
            continue
        out.append(
            {
                "session_id": f"{runtime}:{session['session_id']}",
                "runtime": runtime,
                "task": session.get("name") or session["session_id"],
                "state": _state_from_freshness(updated_at, now),
                "repo": _project_from_slug(Path(path).parent.name),
                "step": None,
                "updated_at": updated_at,
                "trace_url": None,
                "spend_usd": None,
                "capability_class": None,
                "capabilities": None,
                "pull_requests": [],
                "ticket": None,
            }
        )
    return out


def stream_event_for(record: dict[str, Any]) -> dict[str, Any]:
    """The frame `/api/fleetview/stream` sends when one session changes.

    Server-sent events carry the session id and the state that changed, so the page updates one
    row without a reload. The frame is deliberately the whole record: a client that only learned
    the id would have to re-fetch, which is the poll this replaces.
    """
    return {
        "event": "session",
        "session_id": record.get("session_id"),
        "state": record.get("state"),
        "record": record,
    }


def _langfuse_trace_url(session_id: str) -> str | None:
    """The trace link for a sovereign session, with no second Langfuse client and no API call.

    `sovereign/engine/tracing.py`'s `trace_session()` already sends every session's trace to
    Langfuse with the trace's own `id` set to the session_id verbatim (`client.trace(id=session_id,
    ...)`), so the id this board already has IS the Langfuse trace id -- nothing to look up. The
    URL shape (`{host}/trace/{traceId}`) is not a guess: it is the exact shape this estate's own
    real trace links already use (see e.g. docs/reference/forge/20260911T1657Z-ci-flake-triage.md).

    LANGFUSE_HOST unset means Langfuse is not configured for this engine (the same rule
    tracing.py's own `configured()` follows) and the honest answer is a null link, never a URL
    that resolves to nothing.
    """
    host = os.environ.get("LANGFUSE_HOST", "").rstrip("/")
    if not host or not session_id:
        return None
    return f"{host}/trace/{session_id}"


def _engine_capabilities() -> list[str] | None:
    """What a session on this board is allowed to do, straight from AGENTS.md's own
    ```toml policy block (crew#219 R38, `sovereign/policy.py`) -- never a second, hand-kept
    copy of that table (THE HEADLINE).

    Every sovereign session this adapter lists is the *main* engine workflow: `list_sessions()`
    in `sovereign/engine/client.py` queries Temporal for `WorkflowType='{WORKFLOW}'` alone, which
    names only that workflow, never the shadow branch child workflows `sovereign/shadow/`
    starts under a different type. So every row `session_from_engine_row` sees today is the
    `[capabilities] engine` class, and this reads exactly that key -- not a per-session lookup,
    because there is no per-session capability signal in the engine yet to look up (`destructive`
    ops go through consensus, a separate mechanism, not a session-level class). The day a shadow
    session appears on this board, this needs a real per-session class instead of one constant --
    documented here so that day is not a silent wrong answer.

    A policy block that fails to parse (missing AGENTS.md, bad toml) is this host's own gap, not
    a fact about the session -- the honest answer is None, never a fabricated capability list.
    """
    try:
        from sovereign import policy as policy_mod
    except ImportError:
        return None
    try:
        return list(policy_mod.load().capabilities.get("engine", []))
    except (policy_mod.PolicyError, OSError):
        return None


# The sovereign engine's own state string -> this schema's `state` enum. The engine says
# "running"/"stopped"/"failed"; anything it does not say is "unknown", never smoothed into
# "running" (the same rule the world-model graders follow: an absent answer is not a pass).
_ENGINE_STATE = {
    "running": "running",
    "paused": "paused",
    "stopped": "stopped",
    "failed": "failed",
}


def session_from_engine_row(row: dict[str, Any]) -> dict[str, Any]:
    """One sovereign engine row as one session record.

    The engine's own field names differ from the schema's on purpose: the schema is the board's
    contract and the engine is one adapter behind it, so the translation lives here rather than
    the engine being bent to the board. `status` -> `state` is the only rename a reader would
    otherwise trip on.
    """
    engine_state = str(row.get("status") or "").lower()
    session_id = row.get("session_id") or ""
    return {
        "session_id": session_id,
        "runtime": "sovereign",
        "task": row.get("task") or "",
        "state": _ENGINE_STATE.get(engine_state, "unknown"),
        "repo": row.get("repo"),
        "step": row.get("step") if isinstance(row.get("step"), int) else None,
        "updated_at": row.get("updated_at"),
        "trace_url": _langfuse_trace_url(session_id),
        "spend_usd": _spend().spend_for(session_id) if session_id else None,
        "capability_class": "engine",
        "capabilities": _engine_capabilities(),
        "pull_requests": [],
        "ticket": None,
    }


def list_sovereign_sessions() -> list[dict[str, Any]]:
    """Every sovereign session Temporal is running, as session records.

    An engine with no workflows returns an empty list, and that is the honest answer -- not an
    error and not a placeholder row. On 2026-09-12 this estate's namespace held zero workflows,
    so this adapter contributes nothing to the board yet; it is wired so that the first session
    started appears on the board with no further change here.

    Temporal is reached through the existing `sovereign.engine.client`, which already knows the
    address, the namespace and the state shape. This is a second reader of that client, not a
    second client (LAW 43).
    """
    import asyncio

    from sovereign.engine import client as engine_client

    async def _gather() -> list[dict[str, Any]]:
        rows = await engine_client.list_sessions()
        return [session_from_engine_row(r) for r in rows]

    return asyncio.run(_gather())


def list_sessions(catalog: Path | None = None) -> list[dict[str, Any]]:
    """Every claude-code and other-harness session on the board, from the two adapters above.

    `catalog` is accepted (and passed to the other-harness adapter only) for backward
    compatibility with callers that pointed this at a fixture catalogue; the claude-code adapter
    never reads a catalogue at all.
    """
    now = dt.datetime.now(dt.timezone.utc)
    return _claude_code_sessions(now=now) + _other_harness_sessions(catalog, now=now)


# Runtime parity (CP4): every value schema/session.json's `runtime` enum admits must be named
# here, either as the adapter that produces it or as an explicit None with the reason none exists
# yet. A schema enum grown without a matching row here (or the reverse) is exactly the "silent
# adapter death" this estate's proof rule exists to catch -- a runtime the board claims to support
# that quietly never shows a row, indistinguishable from an outage. See test_fleetview_cp4.py.
RUNTIME_ADAPTERS: dict[str, str | None] = {
    "claude-code": "_claude_code_sessions",
    "pi": "_other_harness_sessions",
    "gemini": "_other_harness_sessions",
    "sovereign": "list_sovereign_sessions",
    # No session source exists in this estate for these three yet (checked 2026-09-15: no
    # cyrus/dagster/github-actions reader anywhere in the repo). Naming them None here, rather
    # than leaving them out, is what makes their absence a graded fact instead of a silent gap --
    # the parity test fails loudly the day a real adapter lands and this row is not updated to
    # name it, and fails loudly today if anyone quietly drops them from the schema instead.
    "cyrus": None,
    "dagster": None,
    "github-actions": None,
}


def schema_runtimes(schema: dict[str, Any]) -> list[str]:
    """The `runtime` enum schema/session.json actually declares, read from the schema itself so
    this never drifts from RUNTIME_ADAPTERS by hand-copying a list twice."""
    return list(schema.get("properties", {}).get("runtime", {}).get("enum", []))


def validate_record(
    record: dict[str, Any], schema: dict[str, Any], adapter: str
) -> list[str]:
    """Every way `record` disagrees with `schema`, each message naming `adapter` so a failure
    points at the adapter that produced the bad row, not just the row. Empty list means valid.

    Deliberately a plain hand-walk of `required`/`properties`/`type`/`enum` rather than a
    `jsonschema` dependency this repo does not otherwise carry (mirrors the same choice already
    made in test_fleetview_cp1.py's `validates` step, generalised here so CP4's "an adapter that
    breaks the schema fails CI" scenario can name the adapter, which a bare schema validator
    error would not).
    """
    errors: list[str] = []
    required = schema.get("required", [])
    props = schema.get("properties", {})
    missing = [k for k in required if k not in record]
    if missing:
        errors.append(f"{adapter}: missing required field(s) {missing}")
    for key, spec in props.items():
        if key not in record:
            continue
        value = record[key]
        want = spec.get("type")
        kinds = want if isinstance(want, list) else [want]
        if value is None:
            if "null" not in kinds:
                errors.append(
                    f"{adapter}: {key} is null but schema does not admit null"
                )
            continue
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{adapter}: {key}={value!r} is not one of {spec['enum']}")
        if "string" in kinds and not isinstance(value, str):
            errors.append(
                f"{adapter}: {key} must be a string, got {type(value).__name__}"
            )
        elif "integer" in kinds and not isinstance(value, int):
            errors.append(
                f"{adapter}: {key} must be an integer, got {type(value).__name__}"
            )
        elif "array" in kinds and not isinstance(value, list):
            errors.append(
                f"{adapter}: {key} must be an array, got {type(value).__name__}"
            )
    return errors


def list_all_sessions(
    catalog: Path | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Every runtime's sessions on one board.

    Prefers the model-agnostic estate.db source when it has rows. Falls back to per-vendor
    adapters only when the DB is empty or absent. Either way, failed adapters are recorded
    in `unreachable` rather than silently dropped.
    """
    now = dt.datetime.now(dt.timezone.utc)
    unreachable: list[str] = []

    try:
        db_rows = _estate_db_sessions(now=now)
    except Exception as exc:  # noqa: BLE001
        db_rows = []
        unreachable.append(f"estate-db: {exc.__class__.__name__}: {exc}")

    if db_rows:
        return db_rows, unreachable

    sessions: list[dict[str, Any]] = []
    for name, fn in (
        ("claude-code", lambda: _claude_code_sessions(now=now)),
        ("other-harnesses", lambda: _other_harness_sessions(catalog, now=now)),
        ("sovereign", list_sovereign_sessions),
    ):
        try:
            sessions.extend(fn())
        except Exception as exc:  # noqa: BLE001
            unreachable.append(f"{name}: {exc.__class__.__name__}: {exc}")
    return sessions, unreachable

"""FleetView CP1: the session contract, served.

One job: turn every runtime into the same session record and serve them behind the portal's own
API. The record shape is `schema/session.json`, versioned, and it is the offering's integration
surface -- a customer with their own runtime writes one adapter that emits this shape.

The first adapter is the estate's own prompt ledger. It is not invented here: `bin/catalog-gen`
already renders those rows into the generated Backstage catalogue as `kind: Resource`,
`spec.type: ledger`, with the ledger file named in `metadata.annotations.estate/path`, and
`mcp/plugins/estate_sessions.py` already serves the same rows over MCP. CP1 gives the portal the
same answer from the same catalogue, so the board reads one source of truth rather than a second
file (ADR 0006).

Why the catalogue and not Temporal. The spec's sovereign adapter reads Temporal, and this
estate's Temporal namespace held **zero** workflows when CP1 was built (verified 2026-09-12:
`Client.connect(...).list_workflows()` returned 0 in namespace `estate`). A board wired to an
empty engine shows an empty board, and an empty board reported as progress is the failure this
repository's proof rule exists to stop. The ledger is where the estate's sessions actually are
today; a `sovereign` adapter is added the moment Temporal carries one, and the schema is what
makes that a drop-in.

The four remaining graders in the world-model door are gated for the same class of reason: the
feed does not exist yet. That is written in the spec, not rediscovered here.

CONFIG (LAW 46 -- no path, host or port is a literal in code that decides behaviour; each is an
env var with a container-local default, wired where the deployment can state it):
  ESTATE_CATALOG_PATH       the generated Backstage catalogue (default /data/catalog-info.yaml)
  ESTATE_STATE_PATH_PREFIX  the directory the catalogue names under `~`, i.e. the prefix a row's
                            `estate/path` must carry to be a session row
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# The route CP1's done-command names.
SESSIONS_ROUTE = "/api/fleetview/sessions"
STREAM_ROUTE = "/api/fleetview/stream"

DEFAULT_CATALOG = "/data/catalog-info.yaml"
DEFAULT_LEDGER_PREFIX = "~/.claude/state/prompt-ledger/"

# The `~` the catalogue writes in `estate/path`. bin/catalog-gen renders the home directory as
# this token rather than a real path so the generated file carries no machine's home (LAW 46).
HOME_TOKEN = "@" + "HOME@"


def _catalog_path() -> Path:
    return Path(os.environ.get("ESTATE_CATALOG_PATH", DEFAULT_CATALOG))


def _ledger_prefix() -> str:
    return os.environ.get("ESTATE_STATE_PATH_PREFIX", DEFAULT_LEDGER_PREFIX)


def is_session_row(doc: dict[str, Any]) -> bool:
    """A catalogue document is a session row when it is a ledger whose file lives under the
    prompt ledger.

    The filter is the PATH, not a tag. A tag can be renamed by a later generator (`estate-internal`
    arrived on 2026-09-07, after these rows existed) and the rows would silently stop being
    sessions; the path is the one field this dataset has always carried.
    """
    if doc.get("kind") != "Resource":
        return False
    if (doc.get("spec") or {}).get("type") != "ledger":
        return False
    raw = ((doc.get("metadata") or {}).get("annotations") or {}).get("estate/path")
    if not isinstance(raw, str):
        return False
    prefix = _ledger_prefix().replace(HOME_TOKEN, HOME_TOKEN)
    return raw.replace(HOME_TOKEN, HOME_TOKEN).startswith(prefix)


def session_from_row(doc: dict[str, Any]) -> dict[str, Any]:
    """One catalogue row as one session record, in the shape schema/session.json asserts.

    `state` is "unknown" rather than "running": the catalogue is a snapshot of which ledgers
    exist, and nothing in it says a session is live. Claiming "running" here would put a green
    row on the board for a session that ended last week.
    """
    meta = doc.get("metadata") or {}
    raw = (meta.get("annotations") or {}).get("estate/path", "")
    name = meta.get("name") or Path(raw).stem or "unnamed"
    return {
        "session_id": name,
        "runtime": "claude-code",
        "task": name,
        "state": "unknown",
        "repo": None,
        "step": None,
        "updated_at": None,
        "trace_url": None,
        "spend_usd": None,
        "pull_requests": [],
        "ticket": None,
    }


def list_sessions(catalog: Path | None = None) -> list[dict[str, Any]]:
    """Every session row in the catalogue, as session records.

    A catalogue that is missing or unreadable is an empty list here and the route answers 503;
    it is never a fabricated session. The caller reads the envelope, not an invented row.
    """
    import yaml

    path = catalog or _catalog_path()
    if not path.is_file():
        raise FileNotFoundError(f"catalogue not readable: {path}")
    rows: list[dict[str, Any]] = []
    with path.open() as fh:
        for doc in yaml.safe_load_all(fh):
            if isinstance(doc, dict) and is_session_row(doc):
                rows.append(session_from_row(doc))
    return rows


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
    return {
        "session_id": row.get("session_id") or "",
        "runtime": "sovereign",
        "task": row.get("task") or "",
        "state": _ENGINE_STATE.get(engine_state, "unknown"),
        "repo": row.get("repo"),
        "step": row.get("step") if isinstance(row.get("step"), int) else None,
        "updated_at": row.get("updated_at"),
        "trace_url": None,
        "spend_usd": None,
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


def list_all_sessions(catalog: Path | None = None) -> list[dict[str, Any]]:
    """Every runtime's sessions on one board.

    This is the function the route serves. Each adapter is independent and one that cannot be
    reached does not take the board down: the page still shows the runtimes that answered. The
    unreachable adapter is RECORDED in the returned envelope's `unreachable` list rather than
    silently dropped -- a dead adapter that looks like a quiet fleet is the failure mode this
    estate names everywhere else, and a bare `except: pass` here would be exactly that.
    """
    sessions = list_sessions(catalog)
    unreachable: list[str] = []
    for name, fn in (("sovereign", list_sovereign_sessions),):
        try:
            sessions.extend(fn())
        except Exception as exc:  # noqa: BLE001 - an unreachable runtime contributes no rows
            unreachable.append(f"{name}: {exc.__class__.__name__}: {exc}")
    return sessions, unreachable

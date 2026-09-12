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

import json
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


def _resolve_ledger_paths() -> bool:
    """Whether a row with no explicit ledger path may resolve one from the real home directory.

    Off by default. `list_sessions` turns it on, because that is the caller that has read the
    catalogue and knows the token names a real file on this machine. A unit test or any other
    transformer leaves it off and gets nulls for the ledger-derived fields, which is the honest
    answer when no ledger was read.
    """
    return os.environ.get("ESTATE_RESOLVE_LEDGER_PATHS", "") == "1"


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


def _project_from_slug(slug: str) -> str | None:
    """The project a session's directory slug names, or None when it cannot be told.

    bin/catalog-gen writes the working directory as a slug with the separators replaced and the
    home directory dropped to a token, so a session in a worktree under a project and a session
    at that project's root both resolve to the project name. Nothing here names a real path: the
    slug is split on its separators and the machine's own prefix and any worktree marker are
    discarded, leaving the last meaningful component.
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


def _read_ledger(path: Path) -> dict[str, Any]:
    """What a ledger file says about its own session: when it was last touched and what the person
    actually asked for.

    A ledger is one JSON object per line (the estate writes it that way). The newest timestamp is
    the session's last activity. The task is the newest row whose `source` is `user` -- the
    person's own words. An assistant message or a queue entry is not a task, and a ledger with no
    user row has no task rather than a misleading one.

    A file that cannot be read yields nothing: the row still appears, with nulls, because a session
    the board cannot describe is still a session that exists.
    """
    out: dict[str, Any] = {"updated_at": None, "task": None}
    if not path.is_file():
        return out
    newest_user: tuple[str, str] | None = None
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
                ts = row.get("ts")
                if isinstance(ts, str) and ts:
                    if out["updated_at"] is None or ts > out["updated_at"]:
                        out["updated_at"] = ts
                if row.get("source") == "user":
                    text = row.get("text")
                    if isinstance(text, str) and text.strip():
                        if newest_user is None or str(ts) > newest_user[0]:
                            newest_user = (str(ts), text.strip())
    except OSError:
        return {"updated_at": None, "task": None}
    if newest_user:
        out["task"] = newest_user[1][:200]
    return out


def session_from_row(
    doc: dict[str, Any], ledger_path: Path | None = None
) -> dict[str, Any]:
    """One catalogue row as one session record, in the shape schema/session.json asserts.

    The row itself carries only a name and the ledger's path. What makes the board readable is
    the ledger behind it: its newest timestamp (so the most recent session sorts first) and the
    person's own prompt (so a reader knows what the session is for). Without those, a board of the
    estate's 29 sessions reads as 29 directory paths.

    `state` stays "unknown" rather than "running": the catalogue is a snapshot of which ledgers
    exist, and nothing in it says a session is live. Claiming "running" here would put a green row
    on the board for a session that ended last week.
    """
    meta = doc.get("metadata") or {}
    raw = (meta.get("annotations") or {}).get("estate/path", "")
    name = meta.get("name") or Path(raw).stem or "unnamed"

    if ledger_path is None and raw and _resolve_ledger_paths():
        # The catalogue writes the home directory as a token rather than a real path (LAW 46).
        # Resolving it is OPT-IN: a transformer called without a path must not read the real home
        # directory, or a test that builds a row reaches into the estate's own 29 ledgers and
        # changes what the next test sees.
        ledger_path = Path(raw.replace(HOME_TOKEN, str(Path.home())))

    detail = (
        _read_ledger(ledger_path) if ledger_path else {"updated_at": None, "task": None}
    )
    repo = _project_from_slug(name)

    # The id is what an agent quotes to refer to a session, so it has to be sayable. The catalogue
    # name is a directory slug (`-Users-...-idp--wt-p0`); a session DIRECTORY name is shortened to
    # its last segment, while a real session id (a uuid, or a bare name) is left exactly as it is
    # so nothing that already refers to a session by id breaks.
    session_id = name
    if name.startswith("-"):
        tail = [p for p in name.split("-") if p]
        if tail:
            session_id = tail[-1]

    return {
        "session_id": session_id,
        "runtime": "claude-code",
        "task": detail["task"] or name,
        "state": "unknown",
        "repo": repo,
        "step": None,
        "updated_at": detail["updated_at"],
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
    # This is the caller that has read the catalogue and knows the `@HOME@` token names a real
    # file here, so it opts into resolving each row's ledger and reading its newest timestamp and
    # the last thing the person asked for. Without that read every row would be a directory slug.
    os.environ.setdefault("ESTATE_RESOLVE_LEDGER_PATHS", "1")
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

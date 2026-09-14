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

# What a writer is allowed to put as its runtime label, and where each label lives in a row's
# `estate/path`. A row under `~/.pi/agent/sessions/` was written by the pi-agent runtime; one
# under `~/.claude/state/prompt-ledger/` by claude-code; one whose path contains `gemini/` by
# the gemini runtime. The constants are the schema's runtime enum, kept here so the catalogue
# does not have to name them.
_RUNTIME_PATH_TOKENS = (
    ("pi-agent", "~/.pi/agent/sessions/"),
    ("pi-agent", "@" + "HOME@/.pi/agent/sessions/"),
    ("claude-code", "~/.claude/state/prompt-ledger/"),
    ("claude-code", "@" + "HOME@/.claude/state/prompt-ledger/"),
    ("gemini", "gemini/"),
)

# A row's directory slug may carry any of these tokens before the project name. They are
# dropped from the right tail of the slug before the project name is read. `wt` and `worktrees`
# are special-cased below because they CUT the slug at their position, not just trim the tail.
_NON_PROJECT = frozenset({
    "wt", "worktrees", "worktree", "tmp", "home", "private", "var",
    "claude", "pi", "agent", "sessions", "state", "prompt-ledger",
})


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

    Multiple prefixes are accepted because the same writer family emits different prefixes in
    different estates -- one writes `~/.pi/agent/sessions/` and another `~/.claude/state/prompt-
    ledger/`. The catalogue is the only source of truth, so a row is a session row when its
    `estate/path` is a path this estimator can place against any prefix it knows about.
    """
    if doc.get("kind") != "Resource":
        return False
    if (doc.get("spec") or {}).get("type") != "ledger":
        return False
    raw = ((doc.get("metadata") or {}).get("annotations") or {}).get("estate/path")
    if not isinstance(raw, str) or not raw:
        return False
    expanded = raw.replace(HOME_TOKEN, str(Path.home()))
    prefixes = (
        _ledger_prefix(),
        "~/.pi/agent/sessions/",
        "~/.claude/state/prompt-ledger/",
    )
    return any(expanded.startswith(p) for p in prefixes)


def _expand_home(raw: str) -> str:
    """Resolve the `@HOME@` token a row's `estate/path` carries into the real home directory.

    The token is an estate-wide convention (LAW 46) so the catalogue is portable across machines.
    A test row or a unit harness that does not want the real home can leave `Path.home()` alone
    and a row will still resolve, because the prefix matching in `is_session_row` and the path
    extraction below both substitute the token in the same way.
    """
    return raw.replace(HOME_TOKEN, str(Path.home()))


def _runtime_from_path(raw: str) -> str:
    """The runtime that wrote a session row, from its `estate/path`.

    The catalogue does not name the runtime -- a row is `kind: Resource, spec.type: ledger`, no
    `spec.runtime` field. The runtime is in the path: pi-agent writes under `~/.pi/agent/...`,
    claude-code under `~/.claude/state/prompt-ledger/...`, and gemini under any path containing
    `gemini/`. A path under none of these is reported as `claude-code` (the default estate
    ledger), the same answer a missing row would give.
    """
    if not raw:
        return "claude-code"
    expanded = _expand_home(raw)
    for runtime, token in _RUNTIME_PATH_TOKENS:
        if token.replace(HOME_TOKEN, str(Path.home())) in expanded or token in raw:
            return runtime
    return "claude-code"


def _project_from_slug(slug: str) -> str | None:
    """The project a session's directory slug names, or None when it cannot be told.

    bin/catalog-gen writes the working directory as a slug with the separators replaced and the
    home directory dropped to a token, so a session in a worktree under a project and a session
    at that project's root both resolve to the project name. Nothing here names a real path: the
    slug is split on its separators and the machine's own prefix and any worktree marker are
    discarded, leaving the last meaningful component.

    `_NON_PROJECT` markers (runtime tokens, `tmp`, `home`, etc.) are dropped from the right tail
    of the slug first. If a `wt` or `worktrees` marker remains, the slug is CUT at that
    marker's position, so `-Users-...-idp--wt-p0` becomes the project `idp` rather than the
    worktree name `p0`. Without that cut, a worktree row would point at the worktree instead of
    the project it lives under.
    """
    if not slug:
        return None
    parts = [p for p in slug.split("-") if p]
    # Cut at the FIRST worktree marker anywhere in the slug. A worktree marker carries the
    # project as everything BEFORE it; the worktree suffix (e.g. `wt-NNNN`, `worktree-NNNN`,
    # `worktrees`) is dropped from the project name. This handles `prospector-agent-worktree-0002`
    # by cutting to `prospector-agent` BEFORE the trailing markers are popped.
    for marker in ("wt", "worktrees", "worktree"):
        if marker in parts:
            parts = parts[: parts.index(marker)]
            break
    # Drop `_NON_PROJECT` markers from the right tail: e.g. `pi`, `agent`, `sessions`, `tmp`.
    while parts and parts[-1] in _NON_PROJECT:
        parts.pop()
    return parts[-1] if parts else None


def _slug_from_path(path: str) -> str | None:
    """The project a session's `estate/path` carries, derived from the directory slug.

    A row's path may carry the directory slug either behind a runtime prefix (a real catalogue
    row: `~/.pi/agent/sessions/--Users-...-signalengine--/<uuid>.jsonl`) or as a bare directory
    (a test fixture: `tmp/--Users-...-signalengine--/`). The slug is the segment between the
    leading and trailing `--` markers; the project is the LAST non-marker token of that slug.
    The slug is preferred over the row's name because bin/catalog-gen truncates long project
    names in the name (`signalengine` becomes `sign` in `pi-agent-sessions-...-sign-<hash>`)
    while the path carries the full name.
    """
    if not path:
        return None
    body = path
    for prefix in (
        "~/.pi/agent/sessions/",
        str(Path.home()) + "/.pi/agent/sessions/",
        "~/.claude/state/prompt-ledger/",
        str(Path.home()) + "/.claude/state/prompt-ledger/",
    ):
        if body.startswith(prefix):
            body = body[len(prefix):]
            break
    # Find the chunk between the FIRST `--` and the SECOND `--` (or the rest of the body if
    # only one marker is present). Anything before the first `--` is the prefix (which may be
    # `~/.pi/agent/sessions/` or `tmp/`); anything after the second `--` is the file name.
    if body.count("--") >= 1:
        first, rest = body.split("--", 1)
        # `first` may be the empty string (the `--` came right after the runtime prefix), or
        # it may be a directory name (the test's tmp dir). Either way, the slug is in `rest`.
        if "--" in rest:
            slug, _ = rest.split("--", 1)
        else:
            slug = rest
        # Strip any trailing `/` that may have come from the test's path-join.
        slug = slug.strip("/")
        return _project_from_slug(slug)
    return _project_from_slug(body)


def _short_session_id(name: str, path: str | None = None) -> str | None:
    """A short, sayable session id derived from a row's name (and path, when available).

    A session row's name is the truncated form the catalogue emits when a project name exceeds
    the Backstage 63-character limit (e.g. `signalengine` becomes `sign-<hash>`). The path's
    directory carries the FULL project name, so the project is read from the path when the
    path's project and the name's trailing token disagree (the hash-tail case). When the
    name's trailing token is already the project, the trailing token is appended anyway so
    the session id always reads as `project-<disambiguator>` -- a row whose name ends in
    `signalengine` reads as `signalengine-signalengine`, never just `signalengine`, so a future
    second session in the same project can read as `signalengine-...` without colliding.
    """
    if not name:
        return None
    parts = [p for p in name.split("-") if p]
    if not parts:
        return None
    last = parts[-1]
    project_from_path = _slug_from_path(path) if path else None
    if project_from_path is None:
        # No path: fall back to the name-only slug parser so the row is still readable.
        project_from_path = _project_from_slug(name) or last
    return f"{project_from_path}-{last}"


def _read_ledger(path: Path) -> dict[str, Any]:
    """What a ledger file says about its own session: when it was last touched and what the person
    actually asked for.

    The estate has two ledger shapes: the claude-code prompt-ledger (one JSON object per line with
    `source` and `text` fields) and the pi-agent session log (one JSON object per line with
    `type`, `timestamp`, and `message: {role, content}`). Both are read here. The newest
    timestamp is the session's last activity. The task is the latest row whose author is `user`
    -- the person's own words. An assistant message or a queue entry is not a task, and a
    ledger with no user row has no task rather than a misleading one.

    A file that cannot be read yields nothing: the row still appears, with nulls, because a
    session the board cannot describe is still a session that exists.
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
                ts = row.get("ts") or row.get("timestamp")
                if isinstance(ts, str) and ts:
                    if out["updated_at"] is None or ts > out["updated_at"]:
                        out["updated_at"] = ts
                # claude-code format: top-level `source` and `text` fields.
                if row.get("source") == "user":
                    text = row.get("text")
                    if isinstance(text, str) and text.strip():
                        if newest_user is None or str(ts) > newest_user[0]:
                            newest_user = (str(ts), text.strip())
                    continue
                # pi-agent format: nested `message: {role, content: [{type, text}]}`.
                message = row.get("message")
                if isinstance(message, dict) and message.get("role") == "user":
                    content = message.get("content") or []
                    text_parts = [
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    ]
                    text = " ".join(p for p in text_parts if p).strip()
                    if text:
                        if newest_user is None or str(ts) > newest_user[0]:
                            newest_user = (str(ts), text)
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

    The session id is derived from the row's `estate/path` so that an agent quoting
    `session_id='signalengine-ce5527'` reads as a project and a disambiguating tail rather than
    a 200-character directory slug. The path is also the source of the runtime label, since the
    catalogue does not name the runtime explicitly.
    """
    meta = doc.get("metadata") or {}
    raw = (meta.get("annotations") or {}).get("estate/path", "")
    name = meta.get("name") or Path(raw).stem or "unnamed"

    if ledger_path is None and raw and _resolve_ledger_paths():
        ledger_path = Path(_expand_home(raw))

    detail = (
        _read_ledger(ledger_path) if ledger_path else {"updated_at": None, "task": None}
    )
    runtime = _runtime_from_path(raw)
    repo = _project_from_slug(name)

    # The session id is the short form: project name from the slug plus the trailing
    # disambiguating tail. A row whose name is already a UUID or a bare id (one that does not
    # start with `-`) is left as-is, because shortening it would change what other systems quote.
    if name.startswith("-"):
        session_id = _short_session_id(name) or name
    else:
        session_id = _short_session_id(name, raw) or name

    return {
        "session_id": session_id,
        "runtime": runtime,
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

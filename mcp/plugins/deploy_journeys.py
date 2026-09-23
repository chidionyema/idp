"""Datasette plugin: the `list_deploy_journeys` and `get_deploy_journey` MCP tools.

What this is (crew#973 CP1). The Deploy River
(docs/specs/2026-09-23-deploy-river.md) renders every commit's road from push to
cluster. The renderer, the voice narrator and Telegram all ask the same question --
"what happened to this sha, in order?" -- and ADR 0006 says the platform answers over
the ONE estate MCP server, never a second door. This file is that answer for deploys,
registered via datasette-mcp's `register_mcp_tools(datasette, mcp)` exactly as
`estate_sessions.py` and the rest do.

Data source. `catalog/estate.db`'s `deploy_journeys` / `deploy_journey_events` tables,
written by `bin/estate-deploy-recorder`. One store (THE HEADLINE): the recorder writes,
this reads. Nothing here writes.

Envelope shape. The same `available` / `error` discipline as `estate_sessions.py`:
`available: false` means the database itself is unreadable (BLIND -- a broken reader and
an empty pipeline must never look the same); a sha nobody recorded returns
`journey: null` with an `error` naming the miss. Events come back in `seq` order -- the
road in the order it happened, so a renderer never sorts.

No subprocess, no shell, no network. One sqlite3 connection, read-only queries.

CONFIG (LAW 46):
  ESTATE_DB   the catalogue database (default /data/estate.db, the path the
              estate-mcp Deployment mounts; platform/mcp/estate-mcp.yaml wires it)
"""

from __future__ import annotations

import datetime as dt
import inspect
import json
import os
import sqlite3

try:
    from datasette import hookimpl
except ImportError:  # the offline CI venv has no datasette; parsing must still work

    def hookimpl(fn):  # type: ignore
        return fn


def _db_path() -> str:
    return os.environ.get("ESTATE_DB", "/data/estate.db")


def build_envelope(
    journeys: list | None = None,
    journey: dict | None = None,
    error: str | None = None,
    now: dt.datetime | None = None,
    blind: bool = False,
) -> dict:
    """The one skeleton every caller reads, available or not. An error with rows is a
    named miss (available); an error with no rows is BLIND only when the caller says so
    (the reader could not connect, distinguish that from a sha nobody recorded)."""
    available = (not blind) and (
        journeys is not None or journey is not None or error is not None
    )
    return {
        "available": available,
        "generated_at": (now or dt.datetime.now(dt.timezone.utc)).isoformat(),
        "error": error,
        "journeys": journeys,
        "journey": journey,
    }


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{_db_path()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def _row_to_journey(row: sqlite3.Row, con: sqlite3.Connection) -> dict:
    events = con.execute(
        "SELECT seq, stage, status, detail_json, ts FROM deploy_journey_events"
        " WHERE sha = ? ORDER BY seq",
        (row["sha"],),
    ).fetchall()
    return {
        "sha": row["sha"],
        "branch": row["branch"],
        "pr_number": row["pr_number"],
        "title": row["title"],
        "state": row["state"],
        "started_at": row["started_at"],
        "merged_at": row["merged_at"],
        "events": [
            {
                "seq": e["seq"],
                "stage": e["stage"],
                "status": e["status"],
                "detail": json.loads(e["detail_json"]),
                "ts": e["ts"],
            }
            for e in events
        ],
    }


def list_deploy_journeys(limit: int = 20) -> dict:
    """Newest journeys first. BLIND (available: false) when the store is unreadable."""
    try:
        con = _connect()
        rows = con.execute(
            "SELECT * FROM deploy_journeys ORDER BY started_at DESC LIMIT ?",
            (max(1, min(int(limit), 100)),),
        ).fetchall()
    except (sqlite3.Error, OSError) as e:
        # The db missing, or the table never created (the recorder has not run here):
        # both are BLIND, named, never an empty fleet.
        return build_envelope(
            error=f"deploy store unreadable at {_db_path()}: {e}", blind=True
        )
    return build_envelope(journeys=[_row_to_journey(r, con) for r in rows])


def get_deploy_journey(sha: str) -> dict:
    """One sha's whole road, events in order. A miss is named, never a blank."""
    sha = (sha or "").strip().lower()
    if not sha:
        return build_envelope(error="get_deploy_journey needs a sha")
    try:
        con = _connect()
        row = con.execute(
            "SELECT * FROM deploy_journeys WHERE sha LIKE ? ORDER BY started_at DESC LIMIT 1",
            (f"{sha}%",),
        ).fetchone()
    except (sqlite3.Error, OSError) as e:
        return build_envelope(
            error=f"deploy store unreadable at {_db_path()}: {e}", blind=True
        )
    if row is None:
        return build_envelope(journey=None, error=f"no journey recorded for {sha!r}")
    return build_envelope(journey=_row_to_journey(row, con))


# Module-level aliases: register_mcp_tools defines same-named locals which would shadow
# these (measured 2026-09-13 on estate_sessions: the tool answered with the repr of its
# own coroutine). Bound out here where nothing shadows them.
_envelope_list_deploy_journeys = list_deploy_journeys
_envelope_get_deploy_journey = get_deploy_journey


@hookimpl
def register_mcp_tools(datasette, mcp):
    @mcp.tool()
    async def list_deploy_journeys(limit: int = 20) -> dict:
        """The fleet's recent deploy journeys, newest first: one MCP tool, one envelope.

        Each journey is one commit's road to the cluster -- sha, branch, PR, state
        (merged | in_flight | failed | abandoned) and every stage event in order
        (pr_opened, check:<name>, merged, reconcile). `available: false` means the
        deploy store itself is unreadable, which is BLIND, never an empty fleet.
        """
        result = _envelope_list_deploy_journeys(limit)
        if inspect.isawaitable(result):
            raise RuntimeError(
                "list_deploy_journeys returned an awaitable: the module-level function "
                "is shadowed and the tool would answer with a coroutine object"
            )
        return result

    @mcp.tool()
    async def get_deploy_journey(sha: str) -> dict:
        """One commit's road from push to cluster, every stage in order.

        Accepts a full or abbreviated sha. `journey: null` with an `error` names a sha
        nobody recorded; `available: false` means the store itself is down. The Deploy
        River replays `events` in `seq` order; the voice narrator reads the same rows.
        """
        result = _envelope_get_deploy_journey(sha)
        if inspect.isawaitable(result):
            raise RuntimeError(
                "get_deploy_journey returned an awaitable: the module-level function "
                "is shadowed and the tool would answer with a coroutine object"
            )
        return result

"""FleetView backend plugin: the two routes CP1's done-command names.

`GET /api/fleetview/sessions` and `GET /api/fleetview/stream` are served from the portal backend at
`backstage/packages/backend/src/`. This module is the plugin's router: it owns the paths, the
envelope and the status codes, and it delegates every decision about what a session IS to
`src/sessions.py`, so the translation lives in exactly one file.

The envelope. A read that cannot produce an answer says so rather than returning an empty board:
  {"available": true,  "sessions": [...], "unreachable": []}
  {"available": false, "error": "...", "sessions": [], "unreachable": [...]}
An empty board and a broken board are different facts and the page must be able to tell them
apart. `unreachable` names each adapter that could not answer, so a dead runtime is visible
instead of looking like a quiet fleet -- the same rule the estate's world-model graders follow
when a grader that cannot run is UNKNOWN rather than a pass.

The stream is server-sent events. A client opens it once and receives one frame per session change;
that is what replaces the old 3-second poll (the retired cockpit). The event shape comes from
`sessions.stream_event_for`.

CONFIG (LAW 46): the catalogue path and the ledger prefix are env vars read in `src/sessions.py`;
nothing about a machine's layout is typed here.
"""

from __future__ import annotations

import json
from typing import Any

# The plugin's own module. Imported by path so the portal's build does not need a workspace entry
# before the routes work; the Backstage package wiring lands with the plugin's package.json.
import importlib.util
from pathlib import Path

_SESSIONS_MODULE = Path(__file__).resolve().parent / "sessions.py"


def _sessions():
    spec = importlib.util.spec_from_file_location(
        "fleetview_sessions_impl", _SESSIONS_MODULE
    )
    # Raised, not asserted: an assert is stripped under `python -O`, and this module then would
    # fail with an AttributeError on None instead of saying the session module could not be loaded.
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load the session module at {_SESSIONS_MODULE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SESSIONS_PATH = "/api/fleetview/sessions"
STREAM_PATH = "/api/fleetview/stream"


def sessions_envelope() -> tuple[dict[str, Any], int]:
    """The body and status for `GET /api/fleetview/sessions`.

    Returns the envelope described in this module's docstring. A catalogue that cannot be read is
    a 503 with `available: false` and the reason -- never a 200 carrying an empty list, which
    would render as "no sessions" on the page when the truth is "the catalogue is gone".
    """
    impl = _sessions()
    try:
        sessions, unreachable = impl.list_all_sessions()
    except Exception as exc:  # noqa: BLE001 - an unreadable source is reported, not disguised
        return {
            "available": False,
            "error": f"{exc.__class__.__name__}: {exc}",
            "sessions": [],
            "unreachable": [],
            "generated_at": _now(),
        }, 503
    return {
        "available": True,
        "error": None,
        "sessions": sessions,
        "unreachable": unreachable,
        "generated_at": _now(),
    }, 200


def stream_frames(records: list[dict[str, Any]]) -> list[str]:
    """The server-sent-event frames for a batch of changed records.

    Each frame is `data: <json>\\n\\n`, which is the SSE wire format. The page reads `session_id`
    and `state` out of it and updates one row without a reload; `record` carries the whole session
    so a client that has not seen it yet can insert it rather than needing a second request.
    """
    impl = _sessions()
    return [f"data: {json.dumps(impl.stream_event_for(r))}\n\n" for r in records]


def _now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.timezone.utc).isoformat()

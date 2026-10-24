"""Live friction feed for /fleet: reads the door's ledger, never re-implements the ranking.

The door (`mcp/plugins/estate_executor.py`) writes one line per steer, bare wait, ceiling refusal
and disk refusal to `~/.estate/friction/events.jsonl` as it acts. `bin/pi-observe --friction` ranks
those lines by (kind, shape) over a window. This module loads that one implementation and streams
its result, exactly as `efficiency_feed` loads `bin/estate-efficiency-report` -- a second ranking
written in Python here would be the eleventh copy of one capability.

WHY THIS EXISTS. AGENTS.md section 3: a safeguard the founder cannot watch deciding is a tool, not
an operating safeguard. The doors were measured, refused and ranked for a day before anything showed
them; idp#7017 is that gap, and this closes it.

The envelope follows the module's rule: an unreadable ledger is `available: false` with the error,
never an empty board. "No friction" and "no measurement" are different facts and the page can tell
them apart -- the same distinction `bin/pi-observe --friction` makes by exiting BLIND.
"""

from __future__ import annotations

import asyncio
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path

_OBSERVE = Path(
    os.environ.get("ESTATE_PI_OBSERVE")
    or Path(__file__).resolve().parents[5] / "bin" / "pi-observe"
)


class ObserveAbsent(RuntimeError):
    """`bin/pi-observe` is not in this image, named rather than raised as a bare path error.

    The catalogue image copies no `bin/`, so a repo-relative helper that is absent in a container is
    an expected state: the route returns `available: false` and says which file is missing, instead
    of a 500 the page shows as a broken board.
    """


def _observe():
    if not _OBSERVE.exists():
        raise ObserveAbsent(str(_OBSERVE))
    loader = importlib.machinery.SourceFileLoader("pi_observe", str(_OBSERVE))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def summary(window_hours: float = 24, limit: int = 8) -> dict:
    """The ranked friction aggregate the door produced, in the shape the tile renders."""
    try:
        observe = _observe()
    except ObserveAbsent as exc:
        return {"available": False, "error": f"pi-observe not in this image: {exc}"}

    path = os.environ.get("ESTATE_FRICTION") or getattr(observe, "FRICTION_DEFAULT", "")
    rows = observe.read_friction(path, window_hours)
    if rows is None:
        # Unreadable ledger: BLIND, never an empty board. `available: false` is the page's signal
        # that the number is unknown; a zero would be a claim nothing measured.
        return {"available": False, "error": f"friction ledger unreadable: {path}"}

    agg = observe.aggregate_friction(rows, window_hours)
    kinds = dict(agg["by_kind"])
    return {
        "available": True,
        "window_hours": window_hours,
        "total": agg["events"],
        "kinds": kinds,
        # A ceiling kill is its own class (idp#7013: a gate budgeting 115s inside a 100s door killed
        # three commits). Surfaced separately so it cannot be averaged away by steers.
        "ceiling_kills": kinds.get("ceiling-kill", 0),
        "disk_refusals": kinds.get("refuse-disk", 0),
        "top": agg["shapes"][:limit],
        "ledger": str(path),
        "reader": "bin/pi-observe --friction",
    }


async def stream(window_hours: float = 24, every_s: float = 5.0):
    """One `friction` frame per tick, so the tile moves without any client-side polling."""
    last = None
    while True:
        body = await asyncio.to_thread(summary, window_hours)
        frame = {**body, "changed": body != last}
        last = body
        yield f"event: friction\ndata: {json.dumps(frame)}\n\n"
        await asyncio.sleep(every_s)

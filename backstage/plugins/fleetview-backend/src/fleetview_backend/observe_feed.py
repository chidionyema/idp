"""Live pi-session feed for /fleet: reads the monitor's receipt, never re-measures the machine.

WHY THIS EXISTS. `bin/pi-observe` was measured, ranked and proven for a day before the founder could
see any of it: the receipt at ~/.estate/pi-observe/latest.json was written every 600s by the launchd
reaper and read by nobody. AGENTS.md section 3 is explicit that a safeguard the founder cannot watch
deciding is a tool, not an operating safeguard -- so this module serves that one receipt and nothing
else. It does not run `ps`, it does not re-rank anything: the process table is measured once, by the
job that is actually scheduled, and every surface reads the same measurement.

The envelope rule, the same one `friction_feed` keeps: an unreadable or absent receipt is
`available: false` WITH the reason, never an empty session list. "No pi processes are running" and
"nothing has looked in 6 hours" are different facts and the tile says which. `stale` is measured
against the reaper's own interval (600s): two missed runs means the monitor stopped, not that the
machine went quiet, and a stopped monitor must not be rendered as an idle one.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

RECEIPT = Path(
    os.environ.get("ESTATE_PI_RECEIPT")
    or Path.home() / ".estate" / "pi-observe" / "latest.json"
)

# The reaper in ~/Library/LaunchAgents/ai.estate.pi-reaper.plist fires every 600s. Two missed runs
# is a stopped monitor, so 900s is the line: under it the tile shows the age, over it the tile says
# STALE and stops presenting the numbers as current.
STALE_AFTER_S = int(os.environ.get("ESTATE_PI_STALE_S") or 900)


def _trim(row: dict) -> dict:
    """One process, reduced to what a tile can render. The receipt stays the record of the rest."""
    return {
        "pid": row.get("pid"),
        "verdict": row.get("verdict"),
        "age_s": row.get("age_s"),
        "cpu_s": round(float(row.get("cpu_s") or 0), 1),
        "cpu_pct": row.get("cpu_pct"),
        "rss_mb": row.get("rss_mb"),
        "tty": row.get("tty"),
        "sockets_established": row.get("sockets_established"),
    }


def summary(limit: int = 8) -> dict:
    """The monitor's last receipt, in the shape the tile renders. Never re-derived."""
    path = RECEIPT
    try:
        raw = path.read_text()
    except FileNotFoundError:
        return {
            "available": False,
            "error": f"no receipt at {path}: nothing has run the monitor on this host yet",
            "receipt": str(path),
        }
    except OSError as exc:
        return {
            "available": False,
            "error": f"receipt unreadable: {exc}",
            "receipt": str(path),
        }
    try:
        body = json.loads(raw)
    except ValueError as exc:
        return {
            "available": False,
            "error": f"receipt is not JSON: {exc}",
            "receipt": str(path),
        }

    age = max(0, round(time.time() - path.stat().st_mtime))
    provenance = body.get("provenance") or {}
    live = body.get("live") or {}
    rows = live.get("processes") or []
    counts = live.get("summary") or {}
    sessions = body.get("sessions") or {}
    return {
        "available": True,
        "receipt": str(path),
        "observed_at": body.get("observed_at"),
        "age_s": age,
        "stale": age > STALE_AFTER_S,
        "stale_after_s": STALE_AFTER_S,
        "host": body.get("host"),
        "verdict": body.get("verdict"),
        "blind": body.get("blind"),
        # Who wrote this: the caller measured from the process ancestry, and the launchd job it
        # found. A receipt that cannot name its writer is the defect this field exists to expose.
        "runner": {
            "started_by": provenance.get("started_by"),
            "job": provenance.get("job"),
        },
        "live": {
            "count": counts.get("live", len(rows)),
            "verdicts": counts.get("verdicts") or {},
            "rss_mb": counts.get("rss_mb"),
            "leaked_rss_mb": counts.get("leaked_rss_mb"),
            "long_lived_cpu_s": counts.get("long_lived_cpu_s"),
            "reaped": counts.get("reaped") or [],
        },
        "sessions": {
            "in_window": sessions.get("in_window"),
            "bytes_read": sessions.get("bytes_read"),
            "totals": sessions.get("totals") or {},
        }
        if sessions
        else None,
        "processes": [_trim(r) for r in rows[:limit]],
    }


async def stream(limit: int = 8, every_s: float = 5.0):
    """One `pi-sessions` frame per tick, so the tile moves with nobody reloading it."""
    last = None
    while True:
        body = await asyncio.to_thread(summary, limit)
        frame = {**body, "changed": body != last}
        last = body
        yield f"event: pi-sessions\ndata: {json.dumps(frame)}\n\n"
        await asyncio.sleep(every_s)

"""FleetView: the Greenlane as it moves -- what is under test and which checks it waits on, every
lane's age and reason, how recent batches ended and why, and where push-to-land time goes.

WHY NOT `greenlane.py`. That reader runs `bin/idp-greenlane status`: four serial `gh api` calls
plus main's checks and every open pull request, 29.5 s measured 2026-10-12, and its output hides
what a live view needs (per-lane `arrived`/`attempts`, the landings, the batch's check runs). This
reads the engine's own record directly -- ONE contents read of `state.json` on
`refs/greenlane/state` (3.9 s measured 2026-10-20) -- and, while a batch is under test, ONE
check-runs read of its tip. Same credential and failure sentences as every other GitHub read here
(agent_jobs.gh_get), so there is no second token path to rotate.

HONESTY. Unreadable is `available: false` with its reason, never an empty queue: "nothing is
landing" and "the lane cannot be read" are different answers and the face speaks them aloud.
A check-runs read that fails leaves the batch with `checks_error`, not with zero checks.
"""

from __future__ import annotations

import base64
import json
import threading
import time
from typing import Any

STATE_REF = "refs/greenlane/state"
CACHE_S = 10.0
RECENT = 10
_LOCK = threading.Lock()
_cache: dict[str, Any] = {"at": 0.0, "body": None}


def _repo() -> str:
    from fleetview_backend import agent_jobs

    return agent_jobs.repo()


def _get(path: str) -> tuple[int, Any]:
    from fleetview_backend import agent_jobs

    return agent_jobs.gh_get(path)


def _pct(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    s = sorted(xs)
    return round(s[min(len(s) - 1, int(q * len(s)))], 1)


def _mins(x: Any) -> float | None:
    return round(float(x), 1) if isinstance(x, (int, float)) else None


def read_state() -> dict[str, Any]:
    """The engine's state.json, decoded. Raises RuntimeError with a sayable reason."""
    status, body = _get(f"/repos/{_repo()}/contents/state.json?ref={STATE_REF}")
    if status != 200 or not isinstance(body, dict) or "content" not in body:
        raise RuntimeError(f"the Greenlane state answered {status}")
    return json.loads(base64.b64decode(body["content"]))


def batch_checks(tip: str) -> list[dict[str, Any]]:
    status, body = _get(f"/repos/{_repo()}/commits/{tip}/check-runs?per_page=100")
    if status != 200 or not isinstance(body, dict):
        raise RuntimeError(f"check runs answered {status}")
    out = []
    for c in body.get("check_runs") or []:
        out.append(
            {
                "name": c.get("name"),
                "status": c.get("status"),
                "conclusion": c.get("conclusion"),
                "started_at": c.get("started_at"),
                "completed_at": c.get("completed_at"),
                "url": c.get("html_url"),
            }
        )
    out.sort(key=lambda c: (c["status"] == "completed", c["name"] or ""))
    return out


def summarise(st: dict[str, Any], now_min: float) -> dict[str, Any]:
    """Pure: the engine's state -> what the face and the board show. Times are engine minutes
    (epoch minutes); every age is computed against `now_min` so a test fixes the clock."""
    lanes = []
    for name, ln in (st.get("lanes") or {}).items():
        arrived = ln.get("arrived")
        lanes.append(
            {
                "name": name,
                "status": ln.get("status"),
                "reason": ln.get("reason") or "",
                "attempts": ln.get("attempts", 0),
                "head": (ln.get("head") or "")[:12],
                "age_min": _mins(now_min - arrived)
                if isinstance(arrived, (int, float))
                else None,
            }
        )
    order = {"testing": 0, "red": 1, "conflict": 2, "pending": 3}
    lanes.sort(key=lambda lane: (order.get(lane["status"], 9), lane["name"]))

    batch = st.get("batch")
    live_batch = None
    if isinstance(batch, dict) and batch.get("tip"):
        live_batch = {
            "id": batch.get("id"),
            "tip": batch["tip"],
            "lanes": [m[0] for m in batch.get("members") or [] if m],
            "age_min": _mins(now_min - batch["started"])
            if isinstance(batch.get("started"), (int, float))
            else None,
        }

    history = st.get("history") or []
    recent = []
    for h in reversed(history[-RECENT:]):
        took = (
            h["verdict_at"] - h["started"]
            if isinstance(h.get("verdict_at"), (int, float))
            and isinstance(h.get("started"), (int, float))
            else None
        )
        recent.append(
            {
                "id": h.get("id"),
                "lanes": h.get("members") or [],
                "outcome": h.get("outcome"),
                "action": h.get("action"),
                "reason": h.get("reason") or "",
                "took_min": _mins(took),
                "ago_min": _mins(now_min - h["verdict_at"])
                if isinstance(h.get("verdict_at"), (int, float))
                else None,
            }
        )

    landings = st.get("landings") or []
    waits = [
        r["landed"] - r["queued"]
        for r in landings
        if isinstance(r.get("landed"), (int, float))
        and isinstance(r.get("queued"), (int, float))
    ]
    cycles = [
        h["verdict_at"] - h["started"]
        for h in history
        if isinstance(h.get("verdict_at"), (int, float))
        and isinstance(h.get("started"), (int, float))
    ]
    outcomes: dict[str, int] = {}
    for h in history:
        k = str(h.get("outcome")) + (f"/{h['action']}" if h.get("action") else "")
        outcomes[k] = outcomes.get(k, 0) + 1
    last_landed = [
        {
            "lane": r.get("lane"),
            "batch": r.get("batch"),
            "waited_min": _mins(r["landed"] - r["queued"])
            if isinstance(r.get("queued"), (int, float))
            else None,
            "ago_min": _mins(now_min - r["landed"])
            if isinstance(r.get("landed"), (int, float))
            else None,
        }
        for r in reversed(landings[-5:])
    ]
    return {
        "lanes": lanes,
        "batch": live_batch,
        "recent": recent,
        "landed": last_landed,
        "timings": {
            "queue_to_land_min": {
                "n": len(waits),
                "p50": _pct(waits, 0.5),
                "p90": _pct(waits, 0.9),
            },
            "batch_cycle_min": {
                "n": len(cycles),
                "p50": _pct(cycles, 0.5),
                "p90": _pct(cycles, 0.9),
            },
            "outcomes": outcomes,
        },
        "landed_total": st.get("landed"),
    }


def sentence(view: dict[str, Any]) -> str:
    """One spoken line: what is under test, what is red and why, else that the lane is quiet."""
    parts = []
    b = view.get("batch")
    if b:
        names = ", ".join(n.removeprefix("lane/") for n in b["lanes"]) or "a batch"
        waiting = [
            c["name"] for c in b.get("checks") or [] if c.get("status") != "completed"
        ]
        failed = [
            c["name"] for c in b.get("checks") or [] if c.get("conclusion") == "failure"
        ]
        s = f"Testing {names}"
        if b.get("age_min") is not None:
            s += f" for {round(b['age_min'])} minutes"
        if failed:
            s += f"; {', '.join(failed)} failed"
        elif waiting:
            s += f"; waiting on {', '.join(waiting[:3])}"
        parts.append(s + ".")
    red = [
        lane
        for lane in view.get("lanes") or []
        if lane["status"] in ("red", "conflict")
    ]
    for lane in red[:2]:
        why = lane["reason"].split(" https://")[0]
        parts.append(
            f"{lane['name'].removeprefix('lane/')} is {lane['status']}: {why}."
        )
    if not parts:
        last = (view.get("landed") or [None])[0]
        parts.append(
            f"Nothing under test. Last landed {last['lane'].removeprefix('lane/')}, "
            f"{round(last['ago_min'])} minutes ago."
            if last and last.get("ago_min") is not None and last.get("lane")
            else "Nothing under test."
        )
    p50 = view.get("timings", {}).get("queue_to_land_min", {}).get("p50")
    if p50 is not None:
        parts.append(f"Push to land is about {round(p50)} minutes.")
    return " ".join(parts)


def live(now: float | None = None) -> dict[str, Any]:
    t = now if now is not None else time.time()
    with _LOCK:
        if _cache["body"] is not None and t - _cache["at"] < CACHE_S:
            return _cache["body"]
    try:
        view = summarise(read_state(), t / 60.0)
        view["available"] = True
    except Exception as e:  # noqa: BLE001 -- every failure becomes a sayable reason
        view = {"available": False, "error": str(e)[:300]}
    if view.get("available") and view.get("batch"):
        try:
            view["batch"]["checks"] = batch_checks(view["batch"]["tip"])
        except Exception as e:  # noqa: BLE001
            view["batch"]["checks_error"] = str(e)[:200]
    if view.get("available"):
        view["sentence"] = sentence(view)
    view["read_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
    with _LOCK:
        _cache.update(at=t, body=view)
    return view

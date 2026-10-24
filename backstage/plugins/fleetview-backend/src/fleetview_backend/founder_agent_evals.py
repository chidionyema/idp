"""Evals on the founder's surface: the round ledger and the live feed, read where they are written.

Founder, 2026-10-23: "the founder surface must monitor evals across the estate in real time."
This module is the *reading* half of `eval/founder-agent/` -- the harness writes
`reports/rounds.json` (one row per round) and `reports/live.jsonl` (one line per turn, as the turn
finishes), and the Fleet surface renders both. It adds no second store and no second measurement:
every number here is a value the harness wrote, re-shaped for display, and a missing file is said
out loud rather than rendered as a zero.

Why a file and not a new bus subscription. The harness runs on the laptop, where the eval target
(the door Otto answers on) is reachable and where the estate's own memory of a round lives. The
in-cluster NATS bus is a ClusterIP, so a laptop harness cannot publish to it without a tunnel; the
harness publishes when `ESTATE_FOUNDER_EVAL_NATS` names a bus it *can* reach (it records the
attempt in `live.jsonl` either way -- see `eval/founder-agent/gate_live.py`). The surface reads
the ledger for whichever deployment it is in, and when the ledger is not there it says which path
it looked for. A panel that shows "no rounds yet" over a missing file would be a green light for
an eval nobody ran, which is the defect this estate keeps paying for.

Env (LAW 46 -- one name, no second configuration):
  ESTATE_FOUNDER_EVAL_LEDGER  the rounds file (default: <repo>/eval/founder-agent/reports/rounds.json)
  ESTATE_FOUNDER_EVAL_FEED    the live JSONL  (default: <repo>/eval/founder-agent/reports/live.jsonl)
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

#: The repo-relative default. `parents[5]` is the checkout root in the source tree and `/app` in
#: the catalogue image -- the same shape `efficiency_feed` uses, and the same consequence: in the
#: image the directory is absent, and `EvalsAbsent` names that rather than raising a bare
#: FileNotFoundError into a 500.
#:
#: The ledger is `eval/founder-agent/rounds.json`, NOT `reports/rounds.json`: `run.py` writes it at
#: `HERE / "rounds.json"` beside the harness (see `ROUNDS` in run.py), so an earlier default of
#: `reports/` was a path the harness never writes -- the panel would have answered 503 over a
#: ledger that existed. The feed does live under `reports/` (gate_live's own default).
_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_LEDGER = _ROOT / "eval" / "founder-agent" / "rounds.json"
DEFAULT_FEED = _ROOT / "eval" / "founder-agent" / "reports" / "live.jsonl"

#: How many live lines the surface asks for by default. A round of 12 tasks x 3 runs is 36
#: `run.end` lines plus marks; 200 covers a large suite without shipping a megabyte per poll.
TAIL = 200


class EvalsAbsent(RuntimeError):
    """The harness's ledger is not in this deployment, named. routes.py turns it into a 503."""


def ledger_path() -> Path:
    return Path(
        os.environ.get("ESTATE_FOUNDER_EVAL_LEDGER") or DEFAULT_LEDGER
    ).expanduser()


def feed_path() -> Path:
    return Path(os.environ.get("ESTATE_FOUNDER_EVAL_FEED") or DEFAULT_FEED).expanduser()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvalsAbsent(
            f"no round ledger at {path}: run `eval/founder-agent/run.py --suite --runs 3 --round N` "
            "where the target is reachable, or point ESTATE_FOUNDER_EVAL_LEDGER at the file"
        ) from exc
    except ValueError as exc:
        # A half-written ledger is a real state (the harness rewrites it after every round). Say
        # so; do not report the rounds we could not read as "no rounds".
        raise EvalsAbsent(
            f"the round ledger at {path} is not readable JSON: {exc}"
        ) from exc


def _age_s(at: str | None) -> float | None:
    if not at:
        return None
    try:
        then = dt.datetime.strptime(at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=dt.timezone.utc
        )
    except ValueError:
        return None
    return round((dt.datetime.now(dt.timezone.utc) - then).total_seconds(), 1)


def tail(limit: int = TAIL) -> list[dict[str, Any]]:
    """The last `limit` feed lines, oldest first. Absent file is `[]`, not an error: a checkout
    that has never run a round has an empty feed, and the absence of the *ledger* is what is said
    out loud."""
    try:
        lines = feed_path().read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _verdict_of(row: dict[str, Any]) -> dict[str, str]:
    """The row's gate statuses as one map, from the fields `run.py` actually writes.

    The ledger stores `g1` and `perf` as flat statuses ("pass" / "fail" / "insufficient-data"),
    not a nested map: this re-shapes them for display and invents nothing. A row written by an
    older harness without `perf` shows only the gates it carries.
    """
    verdict: dict[str, str] = {}
    if row.get("g1") is not None:
        verdict["G1"] = str(row["g1"])
    if row.get("perf") is not None:
        verdict["P"] = str(row["perf"])
    if isinstance(row.get("verdict"), dict):  # a pre-2026-10-24 row, kept readable
        verdict.update({str(k): str(v) for k, v in row["verdict"].items()})
    return verdict


def _latest_round_of(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    return sorted(
        rows, key=lambda r: r.get("round") if r.get("round") is not None else -1
    )[-1]


def snapshot(limit: int = TAIL) -> dict[str, Any]:
    """What the panel renders: the ledger, the newest round, and the feed with ages.

    Every field is either a measured value or an explicit absence. `recent_green` is the round
    counter the harness itself keeps (four green of five, spec G9) so the panel cannot disagree
    with the gate about whether the agent is converging.
    """
    state = _read_json(ledger_path())
    rows = list(state.get("rounds") or [])
    latest = _latest_round_of(rows)
    if latest is not None:
        latest = {**latest, "verdict": _verdict_of(latest)}
    # The round counter the gate keeps (G9: four green of the last five). `run.py` returns it but
    # does not persist it, so it is counted here over the same rows -- a count of measured greens,
    # not a second opinion about them.
    last_five = rows[-5:]
    recent_green = sum(1 for r in last_five if r.get("green"))
    feed = tail(limit)
    live = [
        {**e, "age_s": _age_s(e.get("at"))}
        for e in feed
        if e.get("kind")
        in {"round.start", "round.end", "run.end", "feed.not_published"}
    ]
    running = None
    if live:
        last = live[-1]
        # A round is "running" while its session has a `round.start` and no `round.end` after it:
        # the feed is the only honest source for that, and a start with no end is exactly what the
        # founder wants to see while a suite is mid-flight (a `run.end` between them is progress,
        # not a close).
        session = last.get("session_id")
        marks = [e["kind"] for e in live if e.get("session_id") == session]
        if marks and marks[0] == "round.start" and "round.end" not in marks:
            started = [e for e in live if e.get("session_id") == session][0]
            done = sum(
                1
                for e in live
                if e.get("session_id") == session and e["kind"] == "run.end"
            )
            running = {
                "round": session,
                "agent": started.get("agent"),
                "tasks": started.get("tasks"),
                "runs": started.get("runs"),
                "turns_done": done,
                "started_at": started.get("at"),
                "age_s": started.get("age_s"),
            }
    return {
        "ledger": str(ledger_path()),
        "feed": str(feed_path()),
        "latest": latest,
        "running": running,
        "recent_green": recent_green,
        "rounds_measured": len(last_five),
        "rounds": [{**r, "verdict": _verdict_of(r)} for r in rows[-10:]],
        "live": live[-limit:],
    }


def stream(limit: int = TAIL, interval_s: float = 2.0):
    """SSE frames: the snapshot whenever the ledger or the feed changes on disk.

    Polling the mtime is the whole mechanism. A watcher (inotify, watchdog) would be a second
    dependency for a file rewritten a few times a minute, and the founder's own latency budget is
    seconds, not milliseconds.
    """

    async def _frames():
        import asyncio

        last = None
        while True:
            stamp = []
            for p in (ledger_path(), feed_path()):
                try:
                    st = p.stat()
                    stamp.append((st.st_mtime_ns, st.st_size))
                except FileNotFoundError:
                    stamp.append(None)
            key = tuple(stamp)
            if key != last:
                last = key
                try:
                    body = snapshot(limit)
                except EvalsAbsent as exc:
                    body = {"absent": str(exc)}
                yield f"data: {json.dumps(body, default=str)}\n\n"
            await asyncio.sleep(interval_s)

    return _frames()

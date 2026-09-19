"""History and query: the fleet over time, and a way to ask about it.

WHY THIS EXISTS. Measured 2026-09-19: `catalog/estate.db` holds **425 session_events spanning 27
hours** and nothing could read them. The board showed the present instant and threw the rest away,
so "was this agent always slow?" and "when did that start?" were unanswerable.

Prometheus, Grafana and Bloomberg all have this and it is not decoration: an instrument that only
knows NOW cannot tell you whether anything is getting better. That is the difference between a
dashboard and an instrument, and it was the largest capability gap between this and the best.

TWO THINGS, AND THE SECOND IS THE ONE THAT MATTERS:

  1. `history(session_id, since, until)` -- the events a session emitted, in order. The raw
     material. Cheap, and it is what a trail is drawn from.

  2. `query(question)` -- a SMALL, HONEST query language. Not SQL, not PromQL. Four questions a
     person actually asks of a fleet:
         "stuck"                 -- what is stuck, and since when
         "slow"                  -- what has gone quiet relative to its own normal
         "cost"                  -- what has cost the most, and the rate
         "history <id>"          -- one session's timeline
     Anything else returns `unsupported` naming what it CAN answer, because a query language that
     silently returns nothing for a question it does not understand is worse than one that has
     four verbs.

WHY NOT SQL. Because the answer has to arrive by voice in about a second, and a language a person
cannot say out loud is the wrong shape for a room they talk to. Four phrases, each mapped to one
indexed query, each speakable.

THE HONEST LIMIT, stated here rather than discovered later: a session's own events are the only
history that exists. There is no per-minute sampling before 2026-09-18, so "how much did it cost
last Tuesday" is unanswerable and says so. Retrofitting history would mean inventing it.
"""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

# The quiet-relative-to-itself threshold. A session is "slow" when it has gone longer than this
# multiple of its OWN median gap between events. Its own normal, never the fleet's -- a session
# that emits every 10s going quiet for a minute is more alarming than one that emits hourly going
# quiet for an hour, and a fleet-wide threshold cannot see that.
SLOW_GAP_MULTIPLE = 6.0

# How many events a session needs before "its own normal" means anything. Below this the median is
# noise and the honest answer is "not enough history", not a guess.
MIN_EVENTS_FOR_RHYTHM = 8


def _db_path() -> Path:
    import os

    from_env = os.environ.get("ESTATE_DB")
    if from_env:
        return Path(from_env)
    return Path(__file__).resolve().parents[4] / "catalog" / "estate.db"


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(_db_path()))
    con.row_factory = sqlite3.Row
    return con


def _parse(ts: str | None) -> dt.datetime | None:
    if not ts:
        return None
    text = ts.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def history(
    session_id: str,
    since: str | None = None,
    until: str | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """One session's events in order. The raw material a trail is drawn from.

    `session_id` may be the full `runtime:id` the board uses or the bare id the ledger stores; the
    board's own ids are prefixed, so both are matched rather than making a caller strip a prefix
    it saw on screen.
    """
    if not session_id:
        return {"error": "session_id is required", "events": []}
    bare = session_id.rsplit(":", 1)[-1]
    try:
        con = _connect()
    except sqlite3.Error as exc:
        return {"error": f"catalog unreadable: {exc}", "events": []}

    try:
        rows = con.execute(
            """
            SELECT seq, type, payload_json, ts FROM session_events
            WHERE session_id = ?
            ORDER BY seq ASC
            LIMIT ?
            """,
            (bare, max(1, min(limit, 5000))),
        ).fetchall()
    except sqlite3.Error as exc:
        return {"error": f"history unreadable: {exc}", "events": []}
    finally:
        con.close()

    lo, hi = _parse(since), _parse(until)
    out = []
    for r in rows:
        ts = _parse(r["ts"])
        if ts is None:
            continue
        if lo and ts < lo:
            continue
        if hi and ts > hi:
            continue
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except ValueError:
            payload = {}
        out.append({"seq": r["seq"], "type": r["type"], "ts": r["ts"], "payload": payload})

    return {
        "session_id": session_id,
        "count": len(out),
        "from": out[0]["ts"] if out else None,
        "to": out[-1]["ts"] if out else None,
        "events": out,
    }


def _rhythm(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Each session's own cadence: event count, median gap, last event, first event.

    One query, not one per session: this is called on every status question and N+1 round trips on
    an 8GB laptop is the difference between 1.2s and 6s.
    """
    rows = con.execute(
        """
        SELECT session_id, seq, ts FROM session_events
        ORDER BY session_id ASC, seq ASC
        """
    ).fetchall()

    per: dict[str, list[dt.datetime]] = {}
    for r in rows:
        ts = _parse(r["ts"])
        if ts is not None:
            per.setdefault(r["session_id"], []).append(ts)

    out: dict[str, dict[str, Any]] = {}
    for sid, times in per.items():
        gaps = [
            (times[i] - times[i - 1]).total_seconds()
            for i in range(1, len(times))
            if (times[i] - times[i - 1]).total_seconds() > 0
        ]
        gaps.sort()
        median = gaps[len(gaps) // 2] if gaps else 0.0
        out[sid] = {
            "count": len(times),
            "first": times[0].isoformat(),
            "last": times[-1].isoformat(),
            "median_gap_s": median,
            "enough_history": len(times) >= MIN_EVENTS_FOR_RHYTHM,
        }
    return out


def _session_meta(con: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    try:
        rows = con.execute("SELECT id, provider, model, metadata_json FROM sessions").fetchall()
    except sqlite3.Error:
        return out
    for r in rows:
        try:
            meta = json.loads(r["metadata_json"] or "{}")
        except ValueError:
            meta = {}
        out[r["id"]] = {
            "provider": r["provider"],
            "model": r["model"],
            "task": (meta.get("task") or "")[:140],
            "spend_usd": meta.get("spend_usd"),
            "repo": meta.get("repo"),
        }
    return out


def query(directive: str, now: dt.datetime | None = None) -> dict[str, Any]:
    """Four questions, answered from real history. Anything else says what it can answer.

    `directive` is a phrase a person would say, matched case-insensitively on its first word:
        stuck | slow | cost | history <id>

    Returns `{kind, answer, rows, ...}`. `answer` is one sentence, ready to speak.
    """
    now = now or dt.datetime.now(dt.timezone.utc)
    text = (directive or "").strip()
    if not text:
        return {
            "kind": "unsupported",
            "answer": "Ask me stuck, slow, cost, or history followed by a session.",
            "rows": [],
            "supported": ["stuck", "slow", "cost", "history <session>"],
        }
    head, _, rest = text.partition(" ")
    head = head.lower()

    try:
        con = _connect()
    except sqlite3.Error as exc:
        return {"kind": "blind", "answer": f"The catalog is unreadable: {exc}", "rows": []}

    try:
        if head == "stuck":
            return _q_stuck(con, now)
        if head == "slow":
            return _q_slow(con, now)
        if head == "cost":
            return _q_cost(con, now)
        if head == "history":
            return _q_history(con, rest.strip())
        return {
            "kind": "unsupported",
            "answer": (
                f"I do not know how to answer '{text}'. I can answer stuck, slow, cost, "
                "or history followed by a session."
            ),
            "rows": [],
            "supported": ["stuck", "slow", "cost", "history <session>"],
        }
    finally:
        con.close()


def _q_stuck(con: sqlite3.Connection, now: dt.datetime) -> dict[str, Any]:
    """Silent, with a real body of work behind it. Same rule the board's four states use, read
    from history rather than from a single timestamp."""
    rhythm = _rhythm(con)
    meta = _session_meta(con)
    rows = []
    for sid, r in rhythm.items():
        last = _parse(r["last"])
        if last is None:
            continue
        quiet_s = (now - last).total_seconds()
        if quiet_s <= 15 * 60:  # the running window the board uses
            continue
        if not r["enough_history"]:
            # Almost nothing behind it: waiting, not stuck. The distinction the board makes and
            # this must not lose.
            continue
        rows.append(
            {
                "session_id": sid,
                "quiet_minutes": round(quiet_s / 60),
                "events": r["count"],
                "since": r["last"],
                **{k: meta.get(sid, {}).get(k) for k in ("provider", "model", "task", "spend_usd")},
            }
        )
    rows.sort(key=lambda x: -x["quiet_minutes"])
    if not rows:
        return {"kind": "stuck", "answer": "Nothing is stuck.", "rows": []}
    n = len(rows)
    worst = rows[0]
    return {
        "kind": "stuck",
        "answer": (
            f"{n} agent{'s' if n != 1 else ''} stopped producing. "
            f"The longest is {worst['session_id']}, quiet {worst['quiet_minutes']} minutes "
            f"after {worst['events']} events."
        ),
        "rows": rows,
    }


def _q_slow(con: sqlite3.Connection, now: dt.datetime) -> dict[str, Any]:
    """Quiet LONGER THAN ITS OWN NORMAL. The question a fleet-wide threshold cannot answer."""
    rhythm = _rhythm(con)
    rows = []
    for sid, r in rhythm.items():
        if not r["enough_history"] or r["median_gap_s"] <= 0:
            continue
        last = _parse(r["last"])
        if last is None:
            continue
        quiet_s = (now - last).total_seconds()
        expected = r["median_gap_s"]
        if quiet_s > expected * SLOW_GAP_MULTIPLE and quiet_s > 120:
            rows.append(
                {
                    "session_id": sid,
                    "quiet_s": round(quiet_s),
                    "usual_gap_s": round(expected),
                    "times_its_normal": round(quiet_s / expected, 1),
                    "events": r["count"],
                }
            )
    rows.sort(key=lambda x: -x["times_its_normal"])
    if not rows:
        return {
            "kind": "slow",
            "answer": "Nothing is running slower than its own normal.",
            "rows": [],
        }
    worst = rows[0]
    return {
        "kind": "slow",
        "answer": (
            f"{worst['session_id']} is {worst['times_its_normal']}x slower than its own normal — "
            f"usual gap {worst['usual_gap_s']}s, now quiet {worst['quiet_s']}s."
        ),
        "rows": rows,
    }


def _q_cost(con: sqlite3.Connection, now: dt.datetime) -> dict[str, Any]:
    """What has cost the most, and the rate over the events we actually have."""
    meta = _session_meta(con)
    total = sum(
        (m.get("spend_usd") or 0) for m in meta.values() if isinstance(m.get("spend_usd"), (int, float))
    )
    ranked = sorted(
        (
            {"session_id": sid, "spend_usd": m.get("spend_usd"), "events": None, "task": m.get("task")}
            for sid, m in meta.items()
            if isinstance(m.get("spend_usd"), (int, float))
        ),
        key=lambda x: -(x["spend_usd"] or 0),
    )[:8]

    rhythm = _rhythm(con)
    span_s = 0.0
    if rhythm:
        firsts = [_parse(r["first"]) for r in rhythm.values()]
        lasts = [_parse(r["last"]) for r in rhythm.values()]
        firsts = [f for f in firsts if f]
        lasts = [l for l in lasts if l]
        if firsts and lasts:
            span_s = (max(lasts) - min(firsts)).total_seconds()

    rate = (total / (span_s / 3600)) if span_s > 60 else 0.0
    if not ranked:
        return {"kind": "cost", "answer": "No session has a recorded cost yet.", "rows": [], "total_usd": 0}
    worst = ranked[0]
    sentence = f"${total:.2f} across {len(ranked)} sessions."
    if rate > 0:
        sentence += f" ${rate:.2f} an hour over the last {span_s / 3600:.1f} hours."
    sentence += f" The most is {worst['session_id']} at ${(worst['spend_usd'] or 0):.2f}."
    return {
        "kind": "cost",
        "answer": sentence,
        "rows": ranked,
        "total_usd": round(total, 4),
        "rate_usd_per_hour": round(rate, 4),
    }


def _q_history(con: sqlite3.Connection, session_id: str) -> dict[str, Any]:
    if not session_id:
        return {
            "kind": "unsupported",
            "answer": "Say history and then which session.",
            "rows": [],
        }
    h = history(session_id, limit=200)
    if not h.get("events"):
        return {
            "kind": "history",
            "answer": f"No history for {session_id}.",
            "rows": [],
        }
    n = h["count"]
    span = ""
    lo, hi = _parse(h["from"]), _parse(h["to"])
    if lo and hi:
        mins = (hi - lo).total_seconds() / 60
        span = f" over {mins:.0f} minutes"
    return {
        "kind": "history",
        "answer": f"{session_id} emitted {n} events{span}.",
        "rows": h["events"][-40:],
        "session_id": session_id,
    }

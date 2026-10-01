#!/usr/bin/env python3
"""What the laptop router did per lane, from its own ledger, over the last N minutes.

One line per lane the ledger names: calls, refused share, p50/p95 latency and the error the
vendors gave most. The ledger is ~/.estate/efficiency-ledger.jsonl (platform/llm/
efficiency_gateway.py writes one `outcome` row per call it shaped); nothing here talks to a
vendor, so the read is free and safe while the founder is speaking.

WHY. 2026-09-30 the voice think-step was 7.6 s p50 and the only way to see that the `voice`
lane was 78% 429 was a raw read of the ledger from a shell, which prompts the founder on every
session. This is the intent that read.

Usage: router-lane-health.py [--minutes 60] [--lane voice] [--ledger PATH] [--json]
Exit 0 always, unless the ledger cannot be read (2).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_at(s: str) -> datetime | None:
    try:
        return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def error_family(err: str) -> str:
    """The vendor's error reduced to the words that name it, so a Counter groups them."""
    e = err.lower()
    for key, name in (
        ("429", "429 rate-limit"),
        ("rate limit", "429 rate-limit"),
        ("cooldown", "cooldown (all deployments)"),
        ("timeout", "timeout"),
        ("timed out", "timeout"),
        ("401", "401 auth"),
        ("403", "403 forbidden"),
        ("404", "404 model missing"),
        ("400", "400 bad request"),
        ("500", "5xx vendor"),
        ("502", "5xx vendor"),
        ("503", "5xx vendor"),
        ("connection", "connection"),
    ):
        if key in e:
            return name
    return err[:60] or "unnamed"


def summarise(rows: list[dict], since: datetime) -> dict[str, dict]:
    lanes: dict[str, dict] = defaultdict(
        lambda: {
            "calls": 0,
            "ok": 0,
            "latency_ms": [],
            "errors": Counter(),
            "last_error": "",
        }
    )
    for r in rows:
        if r.get("kind") != "outcome":
            continue
        at = parse_at(r.get("at", ""))
        if at is None or at < since:
            continue
        lane = lanes[r.get("model") or "?"]
        lane["calls"] += 1
        if r.get("ok"):
            lane["ok"] += 1
            if isinstance(r.get("latency_ms"), (int, float)):
                lane["latency_ms"].append(float(r["latency_ms"]))
        else:
            fam = error_family(str(r.get("error", "")))
            lane["errors"][fam] += 1
            lane["last_error"] = str(r.get("error", ""))[:160]
    out = {}
    for name, l in lanes.items():
        lat = sorted(l["latency_ms"])
        out[name] = {
            "calls": l["calls"],
            "ok": l["ok"],
            "refused": l["calls"] - l["ok"],
            "refused_pct": round(100.0 * (l["calls"] - l["ok"]) / l["calls"], 1)
            if l["calls"]
            else 0.0,
            "p50_ms": round(statistics.median(lat)) if lat else None,
            "p95_ms": round(lat[min(len(lat) - 1, int(len(lat) * 0.95))])
            if lat
            else None,
            "top_error": l["errors"].most_common(1)[0][0] if l["errors"] else "",
            "last_error": l["last_error"],
        }
    return out


def read_ledger(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--minutes", type=int, default=60)
    ap.add_argument(
        "--lane", default="", help="only this lane (router alias), e.g. voice"
    )
    ap.add_argument(
        "--ledger",
        default=os.environ.get(
            "EFFICIENCY_LEDGER", "~/.estate/efficiency-ledger.jsonl"
        ),
    )
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    path = Path(a.ledger).expanduser()
    if not path.exists():
        print(f"ledger missing: {path}", file=sys.stderr)
        return 2
    since = datetime.fromtimestamp(time.time(), tz=timezone.utc) - timedelta(
        minutes=a.minutes
    )
    lanes = summarise(read_ledger(path), since)
    if a.lane:
        lanes = {k: v for k, v in lanes.items() if k == a.lane}

    if a.json:
        print(
            json.dumps({"minutes": a.minutes, "lanes": lanes}, indent=2, sort_keys=True)
        )
        return 0
    if not lanes:
        print(
            f"no router calls in the last {a.minutes} min"
            + (f" on lane {a.lane}" if a.lane else "")
        )
        return 0
    print(f"{'lane':<16}{'calls':>6}{'refused':>9}{'p50':>8}{'p95':>8}  top error")
    for name in sorted(lanes, key=lambda k: -lanes[k]["calls"]):
        l = lanes[name]
        p50 = f"{l['p50_ms'] / 1000:.2f}s" if l["p50_ms"] is not None else "-"
        p95 = f"{l['p95_ms'] / 1000:.2f}s" if l["p95_ms"] is not None else "-"
        print(
            f"{name:<16}{l['calls']:>6}{l['refused_pct']:>8.1f}%{p50:>8}{p95:>8}  {l['top_error']}"
        )
    worst = [n for n, l in lanes.items() if l["calls"] >= 5 and l["refused_pct"] >= 25]
    for n in worst:
        print(f"\n{n}: last error: {lanes[n]['last_error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

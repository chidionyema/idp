"""FleetView efficiency: what the router's efficiency chain cut, and what the cache saved, live.

One measured source, nothing estimated: the router's own ledger (ESTATE_EFFICIENCY_LEDGER, default
~/.estate/efficiency-ledger.jsonl), written by platform/llm/efficiency_gateway.py on every call
through the router, on every lane:
- "pre" rows: bytes the harness sent vs bytes the router forwarded, and each step's action
  (m7 epoch snapped/locked, m8 reasoning stripped, m1 prefix broken);
- "outcome" rows: what the vendor billed (cache read vs uncached vs cache write);
- "shadow" rows: each background fold of the state document, ok or failed with its reason.

A ledger that cannot be read is reported as unavailable with its reason, never as a zero.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

TAIL_BYTES = (
    32 * 1024 * 1024
)  # a day of rows at the measured 2026-09-29 rate fits in this
WINDOWS = {"hour": timedelta(hours=1), "day": timedelta(days=1)}


def _ledger() -> Path:
    return Path(
        os.path.expanduser(
            os.environ.get("ESTATE_EFFICIENCY_LEDGER")
            or "~/.estate/efficiency-ledger.jsonl"
        )
    )


def _rows(path: Path) -> list[dict[str, Any]]:
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - TAIL_BYTES))
        raw = f.read().decode("utf-8", errors="replace").splitlines()[1:]
    out = []
    for line in raw:
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _empty() -> dict[str, Any]:
    return {
        "calls": 0,
        "bytes_in": 0,
        "bytes_out": 0,
        "epochs_snapped": 0,
        "calls_under_lock": 0,
        "reasoning_bytes_stripped": 0,
        "prefix_broken": 0,
        "prompt_tokens": 0,
        "cache_read_tokens": 0,
        "billed_input_equiv": 0.0,
        "folds_ok": 0,
        "folds_failed": 0,
        "last_fold_error": None,
        "by_lane": {},
    }


def _add(w: dict[str, Any], r: dict[str, Any]) -> None:
    kind = r.get("kind")
    if kind == "pre":
        steps = r.get("steps") or {}
        m7 = steps.get("m7") if isinstance(steps.get("m7"), dict) else {}
        m8 = steps.get("m8") if isinstance(steps.get("m8"), dict) else {}
        m1 = steps.get("m1") if isinstance(steps.get("m1"), dict) else {}
        w["calls"] += 1
        w["bytes_in"] += int(r.get("bytes_before") or 0)
        w["bytes_out"] += int(r.get("bytes_after") or 0)
        w["epochs_snapped"] += m7.get("action") == "snapped"
        w["calls_under_lock"] += m7.get("action") == "locked"
        w["reasoning_bytes_stripped"] += int(m8.get("bytes") or 0)
        w["prefix_broken"] += bool(m1.get("prefix_broken"))
        lane = w["by_lane"].setdefault(
            str(r.get("mode") or "?"), {"calls": 0, "bytes_in": 0, "bytes_out": 0}
        )
        lane["calls"] += 1
        lane["bytes_in"] += int(r.get("bytes_before") or 0)
        lane["bytes_out"] += int(r.get("bytes_after") or 0)
    elif kind == "outcome" and isinstance(r.get("usage"), dict):
        u = r["usage"]
        w["prompt_tokens"] += int(u.get("prompt_tokens") or 0)
        w["cache_read_tokens"] += int(u.get("cache_read") or 0)
        w["billed_input_equiv"] += float(u.get("input_equiv_billed") or 0)
    elif kind == "shadow":
        if r.get("ok"):
            w["folds_ok"] += 1
        else:
            w["folds_failed"] += 1
            w["last_fold_error"] = r.get("error")


def _finish(w: dict[str, Any]) -> dict[str, Any]:
    w["cut_pct"] = (
        round(100 * (1 - w["bytes_out"] / w["bytes_in"]), 2) if w["bytes_in"] else None
    )
    w["cache_hit_pct"] = (
        round(100 * w["cache_read_tokens"] / w["prompt_tokens"], 2)
        if w["prompt_tokens"]
        else None
    )
    w["billed_input_equiv"] = round(w["billed_input_equiv"])
    return w


def efficiency_status(now: datetime | None = None) -> dict[str, Any]:
    path = _ledger()
    try:
        rows = _rows(path)
    except OSError as exc:
        return {"available": False, "error": f"ledger unreadable at {path}: {exc}"}
    now = now or datetime.now(timezone.utc)
    windows = {k: _empty() for k in WINDOWS}
    last = None
    for r in rows:
        try:
            at = datetime.strptime(str(r.get("at")), "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            continue
        last = r.get("at")
        for k, span in WINDOWS.items():
            if now - at <= span:
                _add(windows[k], r)
    return {
        "available": True,
        "last_event_at": last,
        **{k: _finish(w) for k, w in windows.items()},
    }

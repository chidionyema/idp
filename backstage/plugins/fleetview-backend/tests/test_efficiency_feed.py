from __future__ import annotations

import asyncio
import datetime as dt
import json

from fleetview_backend import efficiency_feed


def _rows(now: str) -> list[dict]:
    pre = {
        "v": 2,
        "kind": "pre",
        "at": now,
        "call_id": "c1",
        "mode": "anthropic",
        "bytes_before": 1000,
        "bytes_after": 900,
        "steps": {"m1": {"action": "checked", "prefix_broken": True}},
    }
    out = {
        "v": 2,
        "kind": "outcome",
        "at": now,
        "call_id": "c1",
        "ok": True,
        "model": "claude-sonnet-5-5",
        "usage": {
            "prompt_tokens": 1000,
            "cache_read": 900,
            "uncached_input": 100,
            "output_tokens": 10,
            "input_equiv_billed": 190.0,
            "input_equiv_no_cache": 1000.0,
            "cache_saved_input_equiv": 810.0,
        },
    }
    return [pre, out]


def _ledger(tmp_path, monkeypatch) -> None:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in _rows(now)) + "\n")
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(path))


def test_summary_reports_the_ledger_it_reads(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)
    s = efficiency_feed.summary("1h")
    assert s["calls_billed"] == 1
    assert s["cache_hit_pct"] == 90.0
    assert s["router_bytes_saved"] == 100
    assert (s["prefix_checked"], s["prefix_broken"]) == (1, 1)


def test_stream_emits_an_efficiency_frame_with_the_summary(tmp_path, monkeypatch):
    _ledger(tmp_path, monkeypatch)

    async def first() -> str:
        return await efficiency_feed.stream("1h", every_s=0.01).__anext__()

    frame = asyncio.run(first())
    assert frame.startswith("event: efficiency\ndata: ")
    body = json.loads(frame.split("data: ", 1)[1])
    assert body["calls_billed"] == 1 and body["new_calls"] == 0

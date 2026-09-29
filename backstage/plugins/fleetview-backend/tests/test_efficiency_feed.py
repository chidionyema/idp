from __future__ import annotations
import pytest

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


def test_summary_counts_epochs_and_state_folds(tmp_path, monkeypatch):
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    snap, lock = (
        {**_rows(now)[0], "steps": {"m7": {"action": a}}} for a in ("snapped", "locked")
    )
    folds = [
        {"v": 2, "kind": "shadow", "at": now, "ok": True},
        {"v": 2, "kind": "shadow", "at": now, "ok": False, "error": "groq: 429"},
    ]
    path = tmp_path / "ledger.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in [snap, lock, *folds]) + "\n")
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(path))
    s = efficiency_feed.summary("1h")
    assert (s["epochs_snapped"], s["calls_under_lock"]) == (1, 1)
    assert (s["folds_ok"], s["folds_failed"], s["last_fold_error"]) == (
        1,
        1,
        "groq: 429",
    )


def _proof(trial_lanes):
    return {
        "generated": "2026-09-29T04:00:00Z",
        "trial": {
            "started": None,
            "ends": "2026-10-02T04:00:00Z",
            "lanes": trial_lanes,
        },
        "estimate": {
            "input_usd_billed": 400.0,
            "net_saved_usd": 8.0,
            "steps": {
                "m2": {"what": "collapse", "tokens": 1e6, "net_usd": 1.0},
                "m7": {"what": "epoch compaction", "tokens": 6e6, "net_usd": 7.0},
            },
        },
    }


def _lane(calls, pct, verdict):
    arm = {"conversations": 10, "calls": calls}
    return {
        "treat": arm,
        "control": arm,
        "pct_change_usd_per_call": pct,
        "ci95": [pct - 2, pct + 2],
        "verdict": verdict,
    }


def test_highlights_lead_with_the_top_step_and_only_report_powered_lanes():
    stories = efficiency_feed.highlights(
        _proof(
            {"opus": _lane(50, -12.0, "saves"), "haiku": _lane(3, 5.0, "collecting")}
        )
    )
    assert [s["entity"] for s in stories] == [
        "efficiency/estimate",
        "efficiency/trial/opus",
    ]
    head, trial = stories
    assert "top step m7 $7.00" in head["headline"] and "(2.0%)" in head["headline"]
    assert trial["severity"] == "warn" and "-12.0%" in trial["headline"]
    assert {s["channel"] for s in stories} == {"metrics"}


def test_a_changed_number_is_a_new_story_an_unchanged_one_is_not():
    a = efficiency_feed.highlights(_proof({}))[0]["id"]
    assert efficiency_feed.highlights(_proof({}))[0]["id"] == a
    p = _proof({})
    p["estimate"]["net_saved_usd"] = 9.0
    assert efficiency_feed.highlights(p)[0]["id"] != a


def test_highlights_satisfy_the_news_story_contract():
    import json
    import pathlib

    jsonschema = pytest.importorskip("jsonschema")
    root = pathlib.Path(__file__).resolve().parents[4]
    schema = json.loads(
        (root / "platform/event-bus/contract/estate.news.story.json").read_text()
    )
    for s in efficiency_feed.highlights(_proof({"opus": _lane(50, -12.0, "saves")})):
        jsonschema.validate(s, schema)

"""/fleetview/efficiency reads the router's ledger as written; an unreadable ledger is not a zero."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

_PATH = (
    Path(__file__).resolve().parents[1] / "src" / "fleetview_backend" / "efficiency.py"
)
_SPEC = importlib.util.spec_from_file_location("fleetview_efficiency_under_test", _PATH)
assert _SPEC and _SPEC.loader
efficiency = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(efficiency)

NOW = datetime(2026, 9, 29, 12, 0, tzinfo=timezone.utc)


def _write(path, rows):
    path.write_text("junk-first-line\n" + "\n".join(json.dumps(r) for r in rows) + "\n")


def test_it_reports_cut_cache_and_epochs_per_window(monkeypatch, tmp_path):
    ledger = tmp_path / "l.jsonl"
    _write(
        ledger,
        [
            {
                "kind": "pre",
                "at": "2026-09-29T11:30:00Z",
                "mode": "anthropic",
                "bytes_before": 1000,
                "bytes_after": 200,
                "steps": {"m7": {"action": "snapped"}, "m8": {"bytes": 50}, "m1": {}},
            },
            {
                "kind": "pre",
                "at": "2026-09-29T11:40:00Z",
                "mode": "openai",
                "bytes_before": 1000,
                "bytes_after": 300,
                "steps": {"m7": {"action": "locked"}, "m1": {"prefix_broken": True}},
            },
            {
                "kind": "pre",
                "at": "2026-09-29T02:00:00Z",
                "mode": "openai",
                "bytes_before": 500,
                "bytes_after": 500,
                "steps": {"m7": {"action": "none"}},
            },
            {
                "kind": "outcome",
                "at": "2026-09-29T11:31:00Z",
                "usage": {
                    "prompt_tokens": 100,
                    "cache_read": 90,
                    "input_equiv_billed": 19,
                },
            },
            {
                "kind": "shadow",
                "at": "2026-09-29T11:35:00Z",
                "ok": False,
                "error": "lanes down",
            },
            {"kind": "shadow", "at": "2026-09-29T11:36:00Z", "ok": True},
        ],
    )
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(ledger))
    out = efficiency.efficiency_status(NOW)
    hour, day = out["hour"], out["day"]
    assert out["available"] and out["last_event_at"] == "2026-09-29T11:36:00Z"
    assert (hour["calls"], hour["bytes_in"], hour["bytes_out"], hour["cut_pct"]) == (
        2,
        2000,
        500,
        75.0,
    )
    assert (
        hour["epochs_snapped"],
        hour["calls_under_lock"],
        hour["prefix_broken"],
    ) == (1, 1, 1)
    assert hour["reasoning_bytes_stripped"] == 50 and hour["cache_hit_pct"] == 90.0
    assert (hour["folds_ok"], hour["folds_failed"], hour["last_fold_error"]) == (
        1,
        1,
        "lanes down",
    )
    assert hour["by_lane"]["openai"] == {"calls": 1, "bytes_in": 1000, "bytes_out": 300}
    assert day["calls"] == 3 and day["bytes_in"] == 2500


def test_a_missing_ledger_is_unavailable_not_zero(monkeypatch, tmp_path):
    monkeypatch.setenv("ESTATE_EFFICIENCY_LEDGER", str(tmp_path / "absent.jsonl"))
    out = efficiency.efficiency_status(NOW)
    assert out["available"] is False and "absent.jsonl" in out["error"]

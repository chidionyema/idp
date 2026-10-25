"""The /fleet session feed serves the monitor's receipt, and never turns "nothing looked" into idle.

Measured 2026-10-24: the micro-monitor wrote ~/.estate/pi-observe/latest.json every 600s and no
route served it, so the founder could not see the thing was working (AGENTS.md section 3). These
tests pin the three states the tile must tell apart -- present, STALE, and BLIND -- because a tile
that renders all three as "0 sessions" hides exactly the defect it exists to surface.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from fleetview_backend import observe_feed


def _receipt(**over) -> dict:
    body = {
        "observed_at": "2026-10-24T20:00:30Z",
        "host": "Roses-MBP",
        "provenance": {
            "written_by": "bin/pi-observe",
            "started_by": "launchd",
            "job": {"label": "ai.estate.pi-reaper", "interval_s": 600, "loaded": True},
        },
        "live": {
            "summary": {
                "live": 2,
                "verdicts": {"interactive": 2},
                "rss_mb": 220.5,
                "leaked_rss_mb": 0.0,
                "reaped": [],
            },
            "processes": [
                {
                    "pid": 11,
                    "verdict": "interactive",
                    "age_s": 900,
                    "cpu_s": 12.34,
                    "rss_mb": 110.0,
                },
                {
                    "pid": 12,
                    "verdict": "headless-leaked",
                    "age_s": 4000,
                    "cpu_s": 2.0,
                    "rss_mb": 90.0,
                },
            ],
        },
        "sessions": {"in_window": 3, "bytes_read": 1200, "totals": {"sessions": 3}},
        "verdict": "ok",
    }
    body.update(over)
    return body


@pytest.fixture()
def receipt(tmp_path, monkeypatch):
    path = tmp_path / "latest.json"
    monkeypatch.setattr(observe_feed, "RECEIPT", path)
    return path


def test_a_fresh_receipt_is_served_with_its_writer_and_its_rows(receipt):
    receipt.write_text(json.dumps(_receipt()))
    body = observe_feed.summary()
    assert body["available"] is True
    assert body["stale"] is False
    assert body["live"]["count"] == 2
    assert body["live"]["verdicts"] == {"interactive": 2}
    # Who ran it is part of the answer: a number with no provenance is not evidence.
    assert body["runner"]["started_by"] == "launchd"
    assert body["runner"]["job"]["label"] == "ai.estate.pi-reaper"
    assert [p["pid"] for p in body["processes"]] == [11, 12]


def test_an_old_receipt_is_marked_stale_not_rendered_as_current(receipt):
    receipt.write_text(json.dumps(_receipt()))
    old = time.time() - (observe_feed.STALE_AFTER_S + 60)
    os.utime(receipt, (old, old))
    body = observe_feed.summary()
    assert body["available"] is True
    assert body["stale"] is True, (
        "a monitor that stopped must not look like a quiet machine"
    )


def test_no_receipt_is_blind_with_the_path_not_an_empty_board(receipt):
    body = observe_feed.summary()
    assert body["available"] is False
    assert str(receipt) in body["error"]
    assert "processes" not in body or not body.get("processes")


def test_a_corrupt_receipt_is_blind_and_quotes_the_failure(receipt):
    receipt.write_text("{not json")
    body = observe_feed.summary()
    assert body["available"] is False
    assert "not JSON" in body["error"]


def test_the_row_limit_is_honoured_and_rows_are_trimmed(receipt):
    body = _receipt()
    body["live"]["processes"] = [
        {
            "pid": i,
            "verdict": "interactive",
            "age_s": i,
            "cpu_s": 0.5,
            "rss_mb": 1.0,
            "extra": "x",
        }
        for i in range(1, 20)
    ]
    receipt.write_text(json.dumps(body))
    served = observe_feed.summary(limit=3)
    assert [p["pid"] for p in served["processes"]] == [1, 2, 3]
    assert "extra" not in served["processes"][0], (
        "the tile gets the fields it can render, not the file"
    )


def test_a_blind_pass_is_carried_through_rather_than_hidden(receipt):
    receipt.write_text(
        json.dumps(
            _receipt(
                verdict="BLIND", blind="process table could not be read", live=None
            )
        )
    )
    body = observe_feed.summary()
    assert body["verdict"] == "BLIND"
    assert body["blind"] == "process table could not be read"
    assert body["live"]["count"] == 0

"""The /fleet friction feed reads the door's ledger and never invents a zero.

The distinction under test is the one an eval depends on: an unreadable ledger is BLIND
(`available: false`), an empty ledger is a real zero (`available: true, total: 0`), and the ranking
is `bin/pi-observe`'s, not a second implementation written here.
"""

from __future__ import annotations

import json
import time

import pytest

from fleetview_backend import friction_feed


def _line(kind: str, shape: str, detail: str = "") -> str:
    return json.dumps(
        {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "kind": kind,
            "shape": shape,
            "detail": detail,
        }
    )


@pytest.fixture()
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "events.jsonl"
    monkeypatch.setenv("ESTATE_FRICTION", str(path))
    return path


def test_it_ranks_like_the_door_s_own_reader(ledger):
    ledger.write_text(
        "\n".join(
            [
                _line("steer", "gh api repos/x/y/commits/<sha>/status"),
                _line("steer", "gh api repos/x/y/commits/<sha>/status"),
                _line("steer", "gh api repos/x/y/commits/<sha>/status"),
                _line("refuse-wait", "sleep <n>"),
                _line("ceiling-kill", "pytest -q", "killed at 100s"),
            ]
        )
        + "\n"
    )

    out = friction_feed.summary(24)

    assert out["available"] is True
    assert out["total"] == 5
    assert out["kinds"] == {"steer": 3, "refuse-wait": 1, "ceiling-kill": 1}
    assert out["top"][0]["shape"] == "gh api repos/x/y/commits/<sha>/status"
    assert out["top"][0]["count"] == 3
    # The guard-versus-guard class is surfaced on its own, so steers cannot average it away.
    assert out["ceiling_kills"] == 1


def test_an_empty_ledger_is_a_real_zero(ledger):
    ledger.write_text("")

    out = friction_feed.summary(24)

    assert out["available"] is True
    assert out["total"] == 0
    assert out["top"] == []


def test_an_unreadable_ledger_is_blind_never_zero(ledger, monkeypatch):
    ledger.mkdir()  # a directory where a file belongs: readable path, unreadable content

    out = friction_feed.summary(24)

    assert out["available"] is False
    assert "unreadable" in out["error"]
    assert "total" not in out


def test_the_window_is_honoured(ledger):
    old = json.dumps(
        {"ts": "2020-01-01T00:00:00Z", "kind": "steer", "shape": "gh api <path>"}
    )
    ledger.write_text(old + "\n" + _line("steer", "git status") + "\n")

    out = friction_feed.summary(24)

    assert out["total"] == 1
    assert out["top"][0]["shape"] == "git status"

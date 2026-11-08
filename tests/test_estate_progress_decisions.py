"""A pending approval that is not visible is a black hole (founder, 2026-11-08).

Measured before this fix: `~/.estate/sovereign/decisions.json` held 6 decisions, 2 of them
`state: asked`, and `estate-progress` printed "2 asked"-worth of nothing -- its output did not
contain the string "asked" at all (rg -c asked -> 0), nor any question text. Four decisions had
already expired unanswered behind that silence. The founder's one surface counted his open
decisions and named none of them.

These are FALSIFIERS: put back the count-only behaviour and they fail.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "estate-progress"


def _load():
    loader = importlib.machinery.SourceFileLoader("estate_progress_vis", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _Sources:
    """The smallest thing decision_signals talks to."""

    def __init__(self):
        self.rows = []

    def add(self, name, ok, why="", detail=""):
        self.rows.append({"name": name, "ok": ok, "why": why, "detail": detail})

    def blind(self, name, why):
        self.rows.append({"name": name, "blind": True, "why": why})


def _store(tmp_path, monkeypatch, mod, decisions):
    p = tmp_path / "decisions.json"
    p.write_text(json.dumps({"decisions": decisions}))
    monkeypatch.setattr(mod, "DECISIONS_FILE", p)
    return p


def test_a_pending_decision_is_carried_with_its_question(tmp_path, monkeypatch):
    """The whole point: the question must come back, not a count."""
    mod = _load()
    _store(
        tmp_path,
        monkeypatch,
        mod,
        {
            "dec-9c816eda": {
                "decision_id": "dec-9c816eda",
                "state": "asked",
                "question": "Unblock the three Genesis Argon PRs?",
                "options": [
                    {"key": "approve", "label": "issue the envelope and land them"},
                    {"key": "deny", "label": "leave them draft"},
                ],
            }
        },
    )
    s = _Sources()

    out = mod.decision_signals(s)

    assert out["asked"] == 1
    assert len(out["pending"]) == 1
    p = out["pending"][0]
    assert p["decision_id"] == "dec-9c816eda"
    assert p["question"] == "Unblock the three Genesis Argon PRs?"
    assert [o["key"] for o in p["options"]] == ["approve", "deny"]
    assert "dec-9c816eda" in p["answer_with"]


def test_the_source_line_names_the_pending_decision(tmp_path, monkeypatch):
    """A number with no content is the black hole; the row must name what is waiting."""
    mod = _load()
    _store(
        tmp_path,
        monkeypatch,
        mod,
        {
            "d1": {"decision_id": "dec-aaa", "state": "asked", "question": "Ship it?"},
        },
    )
    s = _Sources()

    mod.decision_signals(s)

    row = next(r for r in s.rows if r["name"] == "decisions")
    assert "AWAITING THE FOUNDER" in row["why"], row
    assert "dec-aaa" in row["why"], row
    assert "Ship it?" in row["why"], row


def test_answered_and_expired_are_not_pending(tmp_path, monkeypatch):
    """Only `asked` needs a human; the rest must not be re-raised as work."""
    mod = _load()
    _store(
        tmp_path,
        monkeypatch,
        mod,
        {
            "a": {"decision_id": "dec-a", "state": "answered", "option": "approve"},
            "b": {"decision_id": "dec-b", "state": "expired"},
            "c": {"decision_id": "dec-c", "state": "asked", "question": "Live one?"},
        },
    )
    s = _Sources()

    out = mod.decision_signals(s)

    assert out["answered"] == 1 and out["expired"] == 1 and out["asked"] == 1
    assert [p["decision_id"] for p in out["pending"]] == ["dec-c"]


def test_an_empty_queue_says_nothing_loud(tmp_path, monkeypatch):
    """When nothing is pending the row must be quiet, not manufacture an alarm."""
    mod = _load()
    _store(
        tmp_path,
        monkeypatch,
        mod,
        {"a": {"decision_id": "dec-a", "state": "answered", "option": "approve"}},
    )
    s = _Sources()

    out = mod.decision_signals(s)

    assert out["pending"] == []
    row = next(r for r in s.rows if r["name"] == "decisions")
    assert "AWAITING" not in row["why"], row


def test_a_missing_store_is_blind_not_silently_empty(tmp_path, monkeypatch):
    """No store must be reported as BLIND -- silence is how a queue disappears."""
    mod = _load()
    monkeypatch.setattr(mod, "DECISIONS_FILE", tmp_path / "nope.json")
    s = _Sources()

    assert mod.decision_signals(s) is None
    assert any(r.get("blind") for r in s.rows), s.rows


def test_the_spoken_sentence_names_the_pending_decision():
    """The sentence is the surface the founder reads and hears. Counted, it still hid 4."""
    mod = _load()
    report = {
        "verdict": {"state": "STUCK"},
        "window_hours": 24,
        "signals": {
            "chain": {
                "landed_in_window": 0,
                "lanes_inflight": 2,
                "oldest_lane_age_min": 12069,
            },
            "decisions": {
                "asked": 1,
                "pending": [
                    {
                        "decision_id": "dec-9c816eda",
                        "question": "Unblock the Argon PRs?",
                    }
                ],
            },
        },
    }

    line = mod.speak(report)

    assert "dec-9c816eda" in line, line
    assert "awaiting you" in line, line


def test_the_spoken_sentence_is_quiet_when_nothing_is_pending():
    mod = _load()
    report = {
        "verdict": {"state": "MOVING"},
        "window_hours": 24,
        "signals": {
            "chain": {
                "landed_in_window": 3,
                "lanes_inflight": 0,
                "oldest_lane_age_min": 4,
            },
            "decisions": {"asked": 0, "pending": []},
        },
    }

    line = mod.speak(report)

    assert "awaiting you" not in line, line

"""bin/idp-objective-miner files an objective only when its baseline was measured in this run.

Founder, 2026-10-19: the research engine read five typed subjects, none with a baseline, so
nothing could show one was answered. An objective with no baseline is refused; one whose
baseline already meets its target is refused; one already open is not filed twice.
"""

from __future__ import annotations

import datetime as dt
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
_loader = importlib.machinery.SourceFileLoader(
    "idp_objective_miner", str(ROOT / "bin" / "idp-objective-miner")
)
_spec = importlib.util.spec_from_loader("idp_objective_miner", _loader)
miner = importlib.util.module_from_spec(_spec)
sys.modules["idp_objective_miner"] = miner  # a dataclass resolves its own module
_loader.exec_module(miner)

STATUS = {
    "main": {"sha": "a" * 40, "required": {"tests": "success", "portal-app": "failure"}, "green": False},
    "state": {"lanes": {
        "lane/a": {"status": "red", "reason": "tests"},
        "lane/b": {"status": "landed"},
        "lane/c": {"status": "conflict"},
    }},
    "work_lost": [{"number": 7, "branch": "lane/x", "head": "b" * 12}],
    "invariants": {"red_open_prs": []},
}


def test_every_non_zero_signal_becomes_an_objective_with_a_measured_baseline():
    ok, refused = miner.admit(miner.mine_greenlane(STATUS))
    assert {o.key for o in ok} == {"main-red", "red-lane", "work-lost"}
    assert refused == []
    lane = next(o for o in ok if o.key == "red-lane")
    assert (lane.baseline, lane.target, lane.count) == (2.0, 0.0, 2)


def test_a_green_estate_files_nothing():
    green = {"main": {"green": True, "required": {}}, "state": {"lanes": {}}, "work_lost": [],
             "invariants": {"red_open_prs": []}}
    assert miner.mine_greenlane(green) == []


def test_no_baseline_no_objective():
    o = miner.Objective("k", "t", "m", None, 0.0, 1, 10, [])
    ok, refused = miner.admit([o])
    assert ok == [] and refused[0][1] == "no baseline measured at intake"


def test_a_baseline_that_already_meets_the_target_is_refused():
    o = miner.Objective("k", "t", "m", 0.0, 0.0, 1, 10, [])
    ok, refused = miner.admit([o])
    assert ok == [] and refused[0][1] == "baseline already meets the target"


def test_ranking_is_pain_per_usd_most_painful_first():
    ok, _ = miner.admit(miner.mine_greenlane(STATUS))
    assert [o.key for o in ok] == ["main-red", "work-lost", "red-lane"]  # 240, 120, 2x45=90 min


def test_the_body_carries_the_identity_marker_and_the_numbers():
    ok, _ = miner.admit(miner.mine_greenlane(STATUS))
    text = miner.body(ok[0], dt.date(2026, 10, 19))
    assert text.startswith("<!-- objective key=main-red -->")
    assert "baseline (measured 2026-10-19):** 1" in text and "deadline:** 2026-11-02" in text


def test_an_open_objective_is_not_filed_twice(monkeypatch):
    calls = []

    def fake_gh(*args):
        calls.append(args)
        class P:  # noqa: D106
            returncode = 0
            stdout = "https://example/issues/1\n"
            stderr = ""
        return P()

    monkeypatch.setattr(miner, "gh", fake_gh)
    monkeypatch.setattr(miner, "open_keys", lambda repo: {"main-red"})
    ok, _ = miner.admit(miner.mine_greenlane(STATUS))
    said = miner.file_all("o/r", ok, dt.date(2026, 10, 19))
    assert "main-red: already open" in said
    created = [c for c in calls if c[:2] == ("issue", "create")]
    assert len(created) == 2

"""Landed is not operational (founder, 2026-11-20 07:35).

Greenlane landed work and stopped; nothing confirmed it deployed, answered its probe or moved its
Optimus metrics, so agents announced success on a push. A landed lane now waits in
`State.verifying` until the backend proves its ship contract live, and the verdict -- pass or
fail with evidence -- is posted by Greenlane, never by the author.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greenlane import engine as E  # noqa: E402

BASE, TIP = "m" * 40, "t" * 40


class World:
    def __init__(self, verdicts):
        self.verdicts = list(verdicts)  # what verify_operational answers, tick by tick
        self.clock = 1000.0
        self.posted: list[tuple[str, str, str]] = []
        self.landed: list[str] = []

    def now(self):
        return self.clock

    def main(self):
        return BASE

    def checks(self, tip):
        return ("green", "")

    def main_red(self, sha):
        return False

    def land(self, members, tip):
        self.landed.append(tip)

    def report(self, *a):
        pass

    def verify_operational(self, lane, rec):
        return self.verdicts.pop(0) if self.verdicts else ("pending", "no answer yet")

    def report_operational(self, lane, rec, verdict, evidence):
        self.posted.append((lane, verdict, evidence))


def _landing(world):
    st = E.State()
    a = E.Lane("lane/a", "ha", seq=1)
    a.status = E.TESTING
    st.lanes["lane/a"] = a
    st.batch = E.Batch("b1", BASE, TIP, [("lane/a", "ha", "ra")], 0.0)
    eng = E.Engine(world, st)
    eng._judge_batch()
    return eng, st


def test_a_landed_lane_waits_for_its_operational_verdict():
    w = World([])
    eng, st = _landing(w)
    assert st.lanes["lane/a"].status == E.LANDED
    assert st.verifying["lane/a"]["tip"] == TIP, "landed is recorded, not taken as done"
    assert w.posted == []


def test_a_passing_contract_is_posted_once_and_leaves_verifying():
    w = World([("pending", "probe 502"), ("pass", "GET -> 200; Optimus read x")])
    eng, st = _landing(w)
    eng._verify_landed()
    assert "lane/a" in st.verifying and w.posted == []
    eng._verify_landed()
    assert st.verifying == {} and w.posted == [
        ("lane/a", "pass", "GET -> 200; Optimus read x")
    ]


def test_a_contract_still_pending_at_its_deadline_fails_with_the_evidence():
    w = World([("pending", "no Optimus reading for x")] * 3)
    eng, st = _landing(w)
    st.verifying["lane/a"]["deadline_min"] = 30
    w.clock += 29
    eng._verify_landed()
    assert "lane/a" in st.verifying and w.posted == []
    w.clock += 2  # The backend clock is MINUTES, not seconds.
    eng._verify_landed()
    assert st.verifying["lane/a"]["state"] == "recovery_required"
    assert st.verifying["lane/a"]["next_action"] == "recover_via_authorised_executor"
    assert w.posted == [
        ("lane/a", "failed", "deadline passed: no Optimus reading for x")
    ]


def test_a_hard_failure_is_posted_at_once():
    w = World([("failed", "landed with no Claim: trailer")])
    eng, st = _landing(w)
    eng._verify_landed()
    assert st.verifying["lane/a"]["state"] == "recovery_required"
    assert w.posted[0][1] == "failed"


def test_a_failed_contract_survives_restart_and_settles_only_after_repair():
    w = World([("failed", "HTTP 525"), ("pending", "HTTP 525"), ("pass", "GET 200")])
    eng, st = _landing(w)
    eng._verify_landed()
    restored = E.State.loads(st.dumps())
    assert restored.verifying["lane/a"]["last"] == "HTTP 525"
    eng = E.Engine(w, restored)
    eng._verify_landed()
    assert len(w.posted) == 1, "failure notification is not spammed"
    assert "lane/a" in restored.verifying
    eng._verify_landed()
    assert restored.verifying == {}
    assert [v for _, v, _ in w.posted] == ["failed", "pass"]


def test_a_failed_operational_receipt_write_never_loses_the_obligation():
    class Refused(World):
        def report_operational(self, lane, rec, verdict, evidence):
            self.posted.append((lane, verdict, evidence))
            return False if len(self.posted) == 1 else True

    w = Refused([("failed", "unauthorised"), ("failed", "unauthorised")])
    eng, st = _landing(w)
    eng._verify_landed()
    assert "lane/a" in st.verifying and not st.verifying["lane/a"].get(
        "failure_reported"
    )
    eng._verify_landed()
    assert st.verifying["lane/a"]["failure_reported"] is True
    assert len(w.posted) == 2, "retry once the receipt door can write"


def test_pass_without_durable_receipt_remains_unsettled():
    class Refused(World):
        def report_operational(self, lane, rec, verdict, evidence):
            return False

    w = Refused([("pass", "HTTP 200")])
    eng, st = _landing(w)
    eng._verify_landed()
    assert "lane/a" in st.verifying
    assert "receipt unavailable" in st.verifying["lane/a"]["last"]


def test_recovery_only_state_cannot_self_dispatch_another_greenlane(monkeypatch):
    import runpy
    from types import SimpleNamespace

    funcs = runpy.run_path(str(Path(__file__).resolve().parents[1] / "bin/idp-greenlane"))
    rearm = funcs["rearm"]
    st = E.State()
    st.verifying["lane/a"] = {
        "state": "recovery_required",
        "head": "a" * 40,
        "last": "HTTP 525",
        "failure_reported": True,
    }
    calls = []
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setitem(rearm.__globals__, "repo", lambda: "o/r")
    monkeypatch.setattr(
        funcs["subprocess"],
        "run",
        lambda argv, **kwargs: (
            calls.append(argv) or SimpleNamespace(returncode=0, stdout="", stderr="")
        ),
    )
    rearm(st)
    assert calls == [], "failed obligations must not spin a privileged runner"
    rearm(st, force=True)
    assert len(calls) == 1, "a real batch resolution still wakes one verification tick"
    assert calls[0][0:3] == ["gh", "workflow", "run"]


def test_verifying_survives_the_state_ref():
    w = World([])
    _, st = _landing(w)
    again = E.State.loads(st.dumps())
    assert again.verifying == st.verifying


def test_a_backend_without_the_verifier_changes_nothing():
    class Old(World):
        verify_operational = None

    w = Old([])
    eng, st = _landing(w)
    eng._verify_landed()
    assert "lane/a" in st.verifying


# -- the GitHub backend's half: the contract is read from the claim, the probe is a GET, and an
# Optimus metric is read by running its registered measure, never from what anyone posts ------

import json  # noqa: E402

from greenlane import github as G  # noqa: E402

CONTRACT = (
    "SHIP-CONTRACT\n"
    "accept: GET https://x.example.test/health expect 200 within 30m\n"
    "optimus: estate.platform_dirs_never_applied baseline=47 target=44\n"
    "failure-classes: gate-blocks-its-own-repair\n"
    "debug-pack: DBG-001"
)


def _backend(monkeypatch, code, readings, comments=()):
    be = G.GitHubBackend.__new__(G.GitHubBackend)
    be.repo = "o/r"
    monkeypatch.setattr(
        be,
        "gh",
        lambda path, *a, **k: {"commit": {"message": "x\n\nClaim: o/r#7\nAgent: a\n"}},
        raising=False,
    )

    def run(*argv, **k):
        if argv[2].endswith("/comments?per_page=100"):
            return json.dumps(list(comments))
        return json.dumps({"body": CONTRACT})

    monkeypatch.setattr(G, "_run", run)
    monkeypatch.setattr(G, "_http_get", lambda url, timeout=20.0: (code, "ok"))
    monkeypatch.setattr(
        be, "_optimus_readings", lambda names: dict(readings), raising=False
    )
    return be


def test_the_probe_failing_keeps_it_pending(monkeypatch):
    be = _backend(monkeypatch, 530, {"estate.platform_dirs_never_applied": 42})
    verdict, why = be.verify_operational("lane/a", {"head": "h"})
    assert verdict == "pending" and "-> 530" in why


def test_an_unmeasured_metric_is_unknown_and_never_a_pass(monkeypatch):
    be = _backend(monkeypatch, 200, {})
    verdict, why = be.verify_operational("lane/a", {"head": "h"})
    assert verdict == "pending" and "estate.platform_dirs_never_applied=UNKNOWN" in why


def test_a_reading_short_of_its_target_is_not_a_pass(monkeypatch):
    be = _backend(monkeypatch, 200, {"estate.platform_dirs_never_applied": 46})
    verdict, why = be.verify_operational("lane/a", {"head": "h"})
    assert verdict == "pending" and "=46 (target 44)" in why


def test_probe_and_a_reading_at_target_pass(monkeypatch):
    be = _backend(monkeypatch, 200, {"estate.platform_dirs_never_applied": 42})
    rec = {"head": "h"}
    verdict, why = be.verify_operational("lane/a", rec)
    assert verdict == "pass", why
    assert rec["claim"] == "o/r#7" and rec["deadline_min"] == 30.0


def test_a_number_posted_on_the_claim_is_not_a_reading(monkeypatch):
    be = _backend(
        monkeypatch,
        200,
        {},
        comments=[{"body": "optimus.estate.platform_dirs_never_applied=1"}],
    )
    verdict, _ = be.verify_operational("lane/a", {"head": "h"})
    assert verdict == "pending"


def test_the_registered_measures_really_measure(monkeypatch):
    be = G.GitHubBackend.__new__(G.GitHubBackend)
    got = be._optimus_readings(
        [
            "estate.platform_dirs_never_applied",
            "claims.ship_contract_enforced",
            "no.such",
        ]
    )
    assert got.get("claims.ship_contract_enforced") == 1.0
    assert isinstance(got.get("estate.platform_dirs_never_applied"), float)
    assert "no.such" not in got

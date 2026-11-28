"""The Greenlane renews the holder's heartbeat for work the holder authored after it.

Root cause, measured 2026-11-28 on lane/meridian-flow-door-v2 (idp#8686): the claim heartbeat was
06:01:35Z, the repair commit was authored 06:17:32Z (15m57s later, so idp#8629's authoring-time
exemption was 57s short), and the Greenlane judged it red: "heartbeat is 32m old (lapse is 15m)".
The renewal that idp#8609 gave a holder's push existed only as a side effect of running the gate on
a laptop. A push through the GitHub API (the thin client), or by a web agent, never ran it, and the
Greenlane judges inside Actions, where the gate wrote nothing. A lease with no way to renew on the
path that was used is a trap, not a rule.

The fix keeps every refusal that matters: CI's ci-success stays read-only; a head with no new
work after the heartbeat is not renewed (an abandoned claim stays lapsed); a rival's newer CLAIM
is never touched.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "claim-gate"
CONTRACT = (
    "SHIP-CONTRACT\n"
    "accept: GET https://voice.example.test/health expect 200 within 30m\n"
    "optimus: claims.ship_contract_enforced baseline=UNKNOWN target=1\n"
    "failure-classes: gate-blocks-its-own-repair\n"
    "debug-pack: DBG-001"
)
MSG = "fix(voice): a thing\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n"
FILES = ["bin/voice-doctor", "tests/test_voice_doctor.py"]
HB = datetime(2026, 11, 28, 6, 1, 35, tzinfo=timezone.utc)
JUDGED = datetime(2026, 11, 28, 6, 34, 0, tzinfo=timezone.utc)  # "32m old"
AUTHORED_LATE = datetime(2026, 11, 28, 6, 17, 32, tzinfo=timezone.utc)  # HB + 15m57s


def _gate():
    loader = importlib.machinery.SourceFileLoader("claim_gate_lane", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _claim(agent="idp-60", hb=HB):
    stamp = hb.strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"CLAIM agent={agent} paths=bin/voice-*,tests/test_voice* heartbeat={stamp}"


def _issue(*claims):
    return {"state": "open", "labels": [], "body": CONTRACT}, [
        {"body": c} for c in claims
    ]


def _judge(issue, made_at, renewer):
    g = _gate()
    g.RENEW = renewer
    out = g.verdict(MSG, FILES, "Mumchimp/idp", lambda r, n: issue, JUDGED, "", made_at)
    return out


def _lane_renewer(calls):
    def renew(repo, num, agent, paths):
        calls.append((repo, num, agent))
        return True

    renew.needs_activity = True
    return renew


def test_the_door_lanes_own_numbers_are_the_lure():
    """Authored 15m57s after the heartbeat: outside idp#8629's window, so read-only judgment is red."""
    assert AUTHORED_LATE - HB > timedelta(minutes=15)
    out = _judge(_issue(_claim()), AUTHORED_LATE, None)
    assert any("heartbeat is" in p and "lapse is 15m" in p for p in out)


def test_the_lane_renewer_replays_the_lure_green():
    calls = []
    out = _judge(_issue(_claim()), AUTHORED_LATE, _lane_renewer(calls))
    assert out == []
    assert calls == [("Mumchimp/crew", 12, "idp-60")]


def test_no_new_work_after_the_heartbeat_is_not_renewed():
    """An abandoned claim stays lapsed: the head was authored BEFORE the heartbeat's window."""
    calls = []
    out = _judge(_issue(_claim()), None, _lane_renewer(calls))
    assert calls == [] and any("heartbeat is" in p for p in out)


def test_a_head_authored_before_the_heartbeat_needs_no_renewal_comment():
    """Already live by idp#8629; the lane must not spam a CLAIM comment every tick."""
    calls = []
    out = _judge(_issue(_claim()), HB - timedelta(minutes=3), _lane_renewer(calls))
    assert out == [] and calls == []


def test_a_rivals_newer_claim_is_never_renewed_over():
    calls = []
    rival = _claim(agent="someone-else", hb=HB + timedelta(minutes=1))
    out = _judge(_issue(_claim(), rival), AUTHORED_LATE, _lane_renewer(calls))
    assert calls == [] and out != []


def test_a_failed_renewal_stays_red():
    def broken(repo, num, agent, paths):
        return False

    broken.needs_activity = True
    out = _judge(_issue(_claim()), AUTHORED_LATE, broken)
    assert any("heartbeat is" in p for p in out)


def test_the_renewer_is_read_only_in_ci_and_writes_only_on_the_lane_flag():
    g = _gate()
    assert g.renewer({"GITHUB_ACTIONS": "true"}) is None
    assert g.renewer({"CI": "true"}) is None
    lane = g.renewer({"GITHUB_ACTIONS": "true", "CLAIM_GATE_RENEW_LANE": "1"})
    assert lane is not None and lane.needs_activity is True
    laptop = g.renewer({})
    assert laptop is not None and laptop.needs_activity is False
    assert g.renewer({"CLAIM_GATE_NO_RENEW": "1"}) is None
    assert (
        g.renewer(
            {
                "GITHUB_ACTIONS": "true",
                "CLAIM_GATE_RENEW_LANE": "1",
                "CLAIM_GATE_NO_RENEW": "1",
            }
        )
        is None
    )


def test_the_greenlane_sets_the_lane_flag():
    src = (SCRIPT.parent.parent / "greenlane" / "github.py").read_text()
    assert '"CLAIM_GATE_RENEW_LANE": "1"' in src

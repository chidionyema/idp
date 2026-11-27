"""A push by a claim's own holder renews its lapsed heartbeat; CI never writes (idp#8609).

Measured 2026-11-27: claude-code waited 20 minutes on another lane, and its next push was refused
"heartbeat is 20m old (lapse is 15m): re-stamp". A push by the holder is the liveness the
heartbeat stands for. A refusal that names its own fix is friction the machine can remove: the
local gate posts the same CLAIM again, with the same paths and a fresh heartbeat, and judges it
live. Only the holder's own newest CLAIM is renewed, which is exactly what a manual re-stamp by
that name does, so nothing passes that a re-stamp would not pass. A rival's newer CLAIM, or
another agent's lapsed one, is never touched. CI judges read-only.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "bin" / "claim-gate"
NOW = datetime(2026, 11, 27, 8, 0, tzinfo=timezone.utc)
CONTRACT = (
    "SHIP-CONTRACT\n"
    "accept: GET https://voice.example.test/health expect 200 within 30m\n"
    "optimus: claims.ship_contract_enforced baseline=UNKNOWN target=1\n"
    "failure-classes: gate-blocks-its-own-repair\n"
    "debug-pack: DBG-001"
)
MSG = "fix(voice): a thing\n\nClaim: Mumchimp/crew#12\nAgent: idp-60\n"
FILES = ["bin/voice-doctor", "tests/test_voice_doctor.py"]


def _gate():
    loader = importlib.machinery.SourceFileLoader("claim_gate_renew", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _claim(agent="idp-60", age=timedelta(minutes=20)):
    hb = (NOW - age).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"CLAIM agent={agent} paths=bin/voice-*,tests/test_voice* heartbeat={hb}"


def _issue(*claims):
    return {"state": "open", "labels": [], "body": CONTRACT}, [
        {"body": c} for c in claims
    ]


def _judge(g, issue, text=MSG, renew=None):
    calls = []

    def recorder(repo, num, agent, paths):
        calls.append((repo, num, agent, paths))
        return renew if isinstance(renew, bool) else True

    g.RENEW = recorder if renew is not None else None
    out = g.verdict(text, FILES, "Mumchimp/idp", lambda r, n: issue, NOW)
    return out, calls


def test_the_holders_lapsed_claim_is_renewed_and_the_push_passes():
    out, calls = _judge(_gate(), _issue(_claim()), renew=True)
    assert out == [], out
    assert calls == [("Mumchimp/crew", 12, "idp-60", "bin/voice-*,tests/test_voice*")]


def test_a_failed_renewal_still_refuses_with_the_restamp():
    out, calls = _judge(_gate(), _issue(_claim()), renew=False)
    assert len(calls) == 1
    assert any("re-stamp" in p for p in out), out


def test_another_agents_lapsed_claim_is_never_renewed():
    text = MSG.replace("Agent: idp-60", "Agent: idp-77")
    out, calls = _judge(_gate(), _issue(_claim()), text=text, renew=True)
    assert calls == []
    assert any("has no live CLAIM" in p for p in out), out


def test_a_rivals_newer_claim_is_never_renewed_over():
    out, calls = _judge(
        _gate(),
        _issue(_claim(), _claim(agent="idp-77", age=timedelta(minutes=30))),
        renew=True,
    )
    assert calls == []
    assert out, "a rival's newest claim must still refuse"


def test_a_live_claim_needs_no_renewal():
    out, calls = _judge(_gate(), _issue(_claim(age=timedelta(minutes=5))), renew=True)
    assert out == [] and calls == []


def test_ci_never_writes_and_a_laptop_does():
    g = _gate()
    assert g.renewer({"GITHUB_ACTIONS": "true"}) is None
    assert g.renewer({"CI": "1"}) is None
    assert g.renewer({"CLAIM_GATE_NO_RENEW": "1"}) is None
    assert callable(g.renewer({}))


if __name__ == "__main__":
    import sys

    if "--optimus" not in sys.argv:
        sys.exit(
            "usage: python3 tests/test_claim_gate_renews_its_own_lapsed_claim.py --optimus"
        )
    g = _gate()
    out, _ = _judge(g, _issue(_claim()), renew=True)
    print(f"optimus.claims.holder_lapse_refusals={1 if out else 0}")

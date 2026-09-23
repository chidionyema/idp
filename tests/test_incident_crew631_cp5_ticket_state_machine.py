"""crew#631 CP5: only the prover moves a ticket to VERIFIED or REJECTED, on a fresh verdict; an
agent's VERIFIED label is reverted; no PASS verdict in 24 h reverts. The decision is a pure
function graded here on literal inputs; the workflow and the App lane are pinned by shape."""

import importlib.machinery
import importlib.util
import json
import time
from pathlib import Path

import yaml

IDP = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader(
    "ticket_verify", str(IDP / "bin" / "idp-ticket-verify")
)
spec = importlib.util.spec_from_loader("ticket_verify", loader)
TV = importlib.util.module_from_spec(spec)
loader.exec_module(TV)

APP = "estate-agents[bot]"
NOW = 1_800_000_000.0


def ts(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def labeled(name, who, at):
    return {
        "event": "labeled",
        "label": {"name": name},
        "actor": {"login": who},
        "created_at": ts(at),
    }


def verdict(done_at, outcome="PASS"):
    return {
        "verdict_id": "v",
        "check_id": "langfuse",
        "target": "t",
        "commit_sha": "0" * 40,
        "artifact_digest": "sha256:abc",
        "config_revision": "1",
        "nonce": "n",
        "started_at": ts(done_at),
        "completed_at": ts(done_at),
        "ttl_seconds": 3600,
        "outcome": outcome,
        "assertions": [
            {"name": "a", "expected": "1", "actual": "1", "ok": outcome == "PASS"}
        ],
        "evidence_ref": "https://example/run/9",
        "prover_id": "estate-ci",
        "prover_run_id": "9",
        "sig": "deadbeef",
    }


def test_an_agent_setting_verified_is_reverted_even_with_a_fresh_pass():
    ev = [
        labeled(TV.PENDING, "agent", NOW - 900),
        labeled(TV.VERIFIED, "agent", NOW - 600),
    ]
    new, why = TV.decide({TV.VERIFIED}, ev, verdict(NOW - 300), NOW, APP)
    assert new == TV.PENDING and "not the prover" in why


def test_a_pending_ticket_is_verified_on_a_fresh_pass_after_the_label():
    ev = [labeled(TV.PENDING, "agent", NOW - 900)]
    new, why = TV.decide({TV.PENDING}, ev, verdict(NOW - 300), NOW, APP)
    assert new == TV.VERIFIED and "sha256:abc" in why and "https://example/run/9" in why


def test_a_pass_older_than_the_label_does_not_verify():
    ev = [labeled(TV.PENDING, "agent", NOW - 100)]
    new, why = TV.decide({TV.PENDING}, ev, verdict(NOW - 300), NOW, APP)
    assert new is None and "predates the label" in why


def test_a_fail_after_the_label_rejects_and_an_expired_verdict_waits():
    ev = [labeled(TV.PENDING, "agent", NOW - 900)]
    new, why = TV.decide({TV.PENDING}, ev, verdict(NOW - 300, "FAIL"), NOW, APP)
    assert new == TV.REJECTED and "FAIL" in why
    new, why = TV.decide({TV.PENDING}, ev, verdict(NOW - 4000), NOW, APP)
    assert new is None and "waiting" in why


def test_verified_by_the_prover_holds_for_24h_then_reverts():
    ev = [
        labeled(TV.PENDING, "agent", NOW - 90_000),
        labeled(TV.VERIFIED, APP, NOW - 80_000),
    ]
    new, why = TV.decide({TV.VERIFIED}, ev, verdict(NOW - 3000), NOW, APP)
    assert new is None
    new, why = TV.decide({TV.VERIFIED}, ev, verdict(NOW - 90_000), NOW, APP)
    assert new == TV.PENDING and "younger than 86400s" in why
    new, why = TV.decide({TV.VERIFIED}, ev, None, NOW, APP)
    assert new == TV.PENDING


def test_an_unsigned_verdict_never_verifies():
    v = verdict(NOW - 300)
    v.pop("sig")
    new, why = TV.decide(
        {TV.PENDING}, [labeled(TV.PENDING, "agent", NOW - 900)], v, NOW, APP
    )
    assert new is None and "no signature" in why


def test_the_workflow_runs_after_the_prover_as_the_app_lane():
    wf = yaml.safe_load((IDP / ".github/workflows/ticket-verification.yml").read_text())
    on = wf[True] if True in wf else wf["on"]
    assert on["workflow_run"]["workflows"] == ["verdict-langfuse"]
    assert on["schedule"][0]["cron"] == "47 * * * *"
    run = wf["jobs"]["verify"]["steps"][-1]["run"]
    assert (
        "bin/idp-github-app token ticket-verifier" in run
        and "bin/idp-ticket-verify" in run
    )
    lanes = json.loads((IDP / "platform/github-app/lanes.json").read_text())
    assert lanes["ticket-verifier"] == {
        "metadata": "read",
        "issues": "write",
        "actions": "read",
    }

"""cp29 acceptance: Trust boundary -- the founder is the root certificate.

Owner: W6 (crew#219). Steps drive sovereign/trust/approval.py, the real
receipt chain and the interventions/ view through `sb approve`'s own
command function. The two fakes sit at true external boundaries:
presence_helper.swift (Touch ID and the Secure Enclave) and the Temporal
signal the approval would send to a running session.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from sovereign import cli as cli_mod
from sovereign.engine import interventions as interventions_mod
from sovereign.engine import receipts as receipts_mod
from sovereign.trust import anchor as anchor_mod
from sovereign.trust import approval

scenarios("features/sovereign-bus/cp29_trust_boundary.feature")

FAKE_ENCLAVE_KEY = b"cp29-fake-secure-enclave"
FAKE_PUBKEY = "cp29-fake-enclave-pubkey"


def _fake_enclave(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand in for presence_helper.swift: the same three verbs, signing
    with a key the test holds. Touch ID itself cannot run under pytest."""

    def helper(args: list[str], timeout: float) -> dict[str, Any] | None:
        verb = args[0]
        if verb == "--sign":
            return {"ok": True, "sig": hmac.new(FAKE_ENCLAVE_KEY, args[1].encode(), hashlib.sha256).hexdigest()}
        if verb == "--pubkey":
            return {"ok": True, "pubkey": FAKE_PUBKEY}
        if verb == "--verify-sig":
            digest, sig, pubkey = args[1], args[2], args[3]
            expected = hmac.new(FAKE_ENCLAVE_KEY, digest.encode(), hashlib.sha256).hexdigest()
            return {"ok": pubkey == FAKE_PUBKEY and hmac.compare_digest(expected, sig)}
        return None

    monkeypatch.setattr(anchor_mod, "_run_helper", helper)
    # The receipt key must stay inside the temporary estate: with the
    # enclave backend pinned, receipts.py would otherwise read the real
    # macOS Keychain item.
    monkeypatch.setattr(receipts_mod, "_keychain_read", lambda: None)
    monkeypatch.setattr(receipts_mod, "_keychain_write", lambda hex_key: False)
    monkeypatch.setenv("SB_TRUST_BACKEND", "secure_enclave")


def _fake_signal(monkeypatch: pytest.MonkeyPatch, context: dict[str, Any]) -> None:
    """The Temporal signal is the session continuing; record it."""

    async def signal(session_id: str, kind: str, by: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        context.setdefault("signals", []).append({"session_id": session_id, "kind": kind, "by": by, **kwargs})
        return {"session_id": session_id, "signal": kind}

    monkeypatch.setattr(cli_mod.engine_client, "signal", signal)


def _approve_in_process(session_id: str, sign: bool, signature: str | None = None) -> int:
    ns = argparse.Namespace(session_id=session_id, by="founder", sign=sign, signature=signature, json=True)
    return cli_mod.cmd_approve(ns)


def _last_receipt_counter() -> int:
    rows = receipts_mod.read_all()
    return int(rows[-1]["counter"]) if rows else 0


# --- Scenario 1: a destructive approval requires a hardware signature -------


@given(parsers.parse('a session asks for "{command}"'))
def _session_asks(config, context: dict[str, Any], command: str) -> None:
    context["session_id"] = "cp29-session"
    context["command"] = command
    context["counter_before"] = _last_receipt_counter()
    context["interventions_before"] = len(interventions_mod.read_all())


@when(parsers.parse('I run "bin/sb approve <session_id> --by founder" without a signature'))
def _run_unsigned(sb, context: dict[str, Any]) -> None:
    result = sb("approve", context["session_id"], "--by", "founder")
    context["refusal"] = result.stderr.strip()
    context["returncode"] = result.returncode


@then(parsers.parse('the command is refused with "{text}"'))
def _refused(config, context: dict[str, Any], text: str) -> None:
    assert context["returncode"] == config.CLI_EXIT_USAGE_ERROR, context
    assert text in context["refusal"], context["refusal"]
    assert context.get("signals", []) == []


@when("the approval is signed with Touch ID")
def _signed_with_touch_id(monkeypatch: pytest.MonkeyPatch, context: dict[str, Any]) -> None:
    _fake_enclave(monkeypatch)
    _fake_signal(monkeypatch, context)
    assert anchor_mod.HardwareTrustAnchor().backend == "secure_enclave"
    context["rc"] = _approve_in_process(context["session_id"], sign=True)


@then("the session continues")
def _continues(context: dict[str, Any]) -> None:
    assert context["rc"] == 0
    signals = context.get("signals", [])
    assert len(signals) == 1 and signals[0]["kind"] == "approve", signals
    assert signals[0]["attestation"] == "hardware"


@then("the intervention log gains one entry with counter n+1 and a valid signature")
def _log_gains_one(context: dict[str, Any]) -> None:
    entries = interventions_mod.read_all()
    assert len(entries) == context["interventions_before"] + 1
    latest = entries[-1]
    assert int(latest["counter"]) == context["counter_before"] + 1
    assert latest["kind"] == "approve" and latest["attestation"] == "hardware"
    assert latest["approval_backend"] == "secure_enclave" and latest["approval_sig"]
    # Valid signature, two ways: the chain and its interventions/ view both
    # verify (HMAC under the estate key, head anchor, watermark), and the
    # enclave key that signed the approval is the one now enrolled.
    assert interventions_mod.verify()["ok"], interventions_mod.verify()
    assert anchor_mod.HardwareTrustAnchor().enrolled_pubkey() == FAKE_PUBKEY


# --- Scenario 2: replay is rejected -----------------------------------------


@given("a captured signed approval")
def _captured(monkeypatch: pytest.MonkeyPatch, config, context: dict[str, Any]) -> None:
    _fake_enclave(monkeypatch)
    challenge = approval.challenge("cp29-replay", cli_mod.APPROVE_ACTION, "founder")
    envelope = approval.sign(challenge, anchor_mod.HardwareTrustAnchor())
    first = approval.verify(envelope)
    assert first["ok"], first
    approval.spend(int(first["counter"]))  # the capture was already acted on once
    context["envelope"] = envelope


@when("it is submitted a second time")
def _replayed(context: dict[str, Any]) -> None:
    context["verdict"] = approval.verify(context["envelope"])


@then(parsers.parse('it is refused with "{text}"'))
def _replay_refused(context: dict[str, Any], text: str) -> None:
    verdict = context["verdict"]
    assert verdict["ok"] is False and verdict["reason"] == text, verdict


# --- Scenario 3: degraded mode is logged, not silent -------------------------


@given("the Secure Enclave is unavailable")
def _no_enclave(monkeypatch: pytest.MonkeyPatch, config, context: dict[str, Any]) -> None:
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    assert anchor_mod.HardwareTrustAnchor().backend != "secure_enclave"
    _fake_signal(monkeypatch, context)
    context["session_id"] = "cp29-degraded"
    context["interventions_before"] = len(interventions_mod.read_all())


@then("approvals fall back to the configured multi-signature set")
def _fallback_set(context: dict[str, Any]) -> None:
    assert _approve_in_process(context["session_id"], sign=True) == 0
    entries = interventions_mod.read_all()
    assert len(entries) == context["interventions_before"] + 1
    latest = entries[-1]
    context["latest"] = latest
    assert latest["approval_backend"] == "multisig"
    assert sorted(latest["approval_signers"]) == sorted(anchor_mod.signer_ids())
    assert len(latest["approval_signers"]) >= 2


@then(parsers.parse('the receipt records "{pair}"'))
def _receipt_records(context: dict[str, Any], pair: str) -> None:
    field, _, value = pair.partition(":")
    latest = context["latest"]
    assert latest[field] == value, latest
    assert context["signals"][-1]["attestation"] == value
    assert interventions_mod.verify()["ok"]

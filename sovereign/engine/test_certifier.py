"""The independent certifier against the REAL compiled gate and the REAL yield verifier.

Nothing here stubs a verdict: `rust_gate_verify_settlement` shells out to the compiled
`meridian-gate`, and `verify_instruction_yield` checks the Ed25519 signature. Only the network
GET is injected, because a unit test cannot reach production.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sovereign.engine import certifier
from sovereign.engine.activities import (
    rust_gate_verify_settlement,
    verify_instruction_yield,
)

TASK = "ship the thing"
URL = "https://llm.meridianlabs.cloud/health"
POLICY = "ef" * 32
ACCEPT = certifier.parse_accept(f'GET {URL} expect 200 contains "ok" within 30m')
EXPECTED = {
    "instruction_id": "INS-77",
    "run_id": "run-abc",
    "epoch": 2,
    "goal_sha256": hashlib.sha256(TASK.encode()).hexdigest(),
    "commit_sha": None,
}


def _gate() -> str:
    root = Path(__file__).resolve().parents[2]
    for cand in (
        os.environ.get("MERIDIAN_GATE_BIN"),
        str(root / "target/release/meridian-gate"),
    ):
        if cand and Path(cand).is_file() and os.access(cand, os.X_OK):
            return cand
    raise AssertionError("compiled meridian-gate not found; these tests never skip it")


def _ok(_url):
    return 200, b'{"status":"ok"}'


@pytest.fixture()
def trust(monkeypatch):
    certifier_key, worker_key = (
        Ed25519PrivateKey.generate(),
        Ed25519PrivateKey.generate(),
    )
    pub = certifier_key.public_key().public_bytes_raw().hex()
    monkeypatch.setenv("MERIDIAN_GATE_BIN", _gate())
    monkeypatch.setenv("ESTATE_YIELD_VERIFIER_PUBKEY_HEX", pub)
    monkeypatch.setenv("ESTATE_SETTLEMENT_CERTIFIERS_HEX", pub)
    monkeypatch.setenv(
        "ESTATE_WORKER_PUBKEY_HEX", worker_key.public_key().public_bytes_raw().hex()
    )
    monkeypatch.setenv("ESTATE_SETTLEMENT_POLICY_HASH", POLICY)
    seed = certifier_key.private_bytes_raw().hex()
    monkeypatch.setenv("CERT_SEED_TEST", seed)
    monkeypatch.setenv("WORKER_SEED_TEST", worker_key.private_bytes_raw().hex())
    return certifier_key


def _verdicts(envelope, expected=EXPECTED):
    payload = {"expected": expected, "envelope": envelope}
    return (
        asyncio.run(rust_gate_verify_settlement(payload)),
        asyncio.run(verify_instruction_yield(payload)),
    )


def _envelope(**over):
    seed_env = over.pop("seed_env", "CERT_SEED_TEST")
    return certifier.build_envelope(
        over.pop("expected", EXPECTED),
        over.pop("accept", ACCEPT),
        seed_env=seed_env,
        policy_hash=over.pop("policy_hash", POLICY),
        getter=over.pop("getter", _ok),
    )


def _boom(_u):
    raise AssertionError("must not be fetched")


def test_certified_effect_is_allowed_by_both_independent_verifiers(trust):
    assert _verdicts(_envelope()) == ("allow", "settle")


def test_observed_effect_that_does_not_match_the_predicate_signs_nothing(trust):
    for getter in (lambda u: (503, b"ok"), lambda u: (200, b"degraded")):
        with pytest.raises(certifier.CertifierRefusal):
            _envelope(getter=getter)


def test_proxy_and_non_https_targets_are_never_observed_or_signed(trust):
    for url in (
        "https://raw.githubusercontent.com/chidionyema/idp/main/README.md",
        "https://localhost/health",
        "https://127.0.0.1/health",
        "https://10.0.0.4/health",
        "https://someone.github.io/x",
    ):
        acc = certifier.Accept(url, 200, "ok")
        with pytest.raises(certifier.CertifierRefusal):
            _envelope(accept=acc, getter=_boom)
    with pytest.raises(certifier.CertifierRefusal):
        certifier.parse_accept(
            "GET http://llm.meridianlabs.cloud/health expect 200 within 30m"
        )


def test_worker_key_cannot_certify_itself(trust):
    assert _verdicts(_envelope(seed_env="WORKER_SEED_TEST")) == ("reject", "reject")


def test_unconfigured_or_bad_seed_refuses(trust, monkeypatch):
    monkeypatch.delenv("CERT_SEED_TEST")
    with pytest.raises(certifier.CertifierRefusal):
        _envelope()
    monkeypatch.setenv("CERT_SEED_TEST", "not-hex")
    with pytest.raises(certifier.CertifierRefusal):
        _envelope()


def test_receipt_for_another_run_epoch_or_goal_is_rejected(trust):
    good = _envelope()
    for field, value in (
        ("run_id", "run-other"),
        ("epoch", 3),
        ("goal_sha256", "0" * 64),
    ):
        assert _verdicts(good, {**EXPECTED, field: value}) == ("reject", "reject")


def test_tampered_envelope_is_rejected(trust):
    env = _envelope()
    forged = {**env, "settlement": {**env["settlement"]}}
    forged["settlement"]["receipt"] = {
        **env["settlement"]["receipt"],
        "observation_url": URL + "x",
    }
    assert _verdicts(forged)[0] == "reject"
    other = {**env, "receipt": {**env["receipt"], "effect_ref": "something-else"}}
    assert _verdicts(other)[1] == "reject"


def test_policy_mismatch_with_the_pinned_host_policy_is_rejected(trust):
    # The yield signature is valid, so only the compiled gate's pinned-policy check refuses.
    assert _verdicts(_envelope(policy_hash="ab" * 32)) == ("reject", "settle")


def test_certifier_key_that_the_host_does_not_pin_is_rejected(trust, monkeypatch):
    outsider = Ed25519PrivateKey.generate()
    monkeypatch.setenv("CERT_SEED_TEST", outsider.private_bytes_raw().hex())
    assert _verdicts(_envelope()) == ("reject", "reject")


def test_expected_from_state_rebuilds_the_workflow_expectation():
    state = {"instruction_id": "INS-77", "task": TASK, "step": 2, "commit": None}
    assert certifier.expected_from_state(state, "run-abc") == EXPECTED
    with pytest.raises(certifier.CertifierRefusal):
        certifier.expected_from_state({"instruction_id": "INS-77", "task": ""}, "r")

"""Tests for sovereign/engine/paid_compute.py (idp#3525 CP1, COST-02).

COST-02's ACCEPT, verbatim: "attempting activation without signature
yields no provisioning call; with signature + quorum, provisioning
proceeds." Each half is its own test below, plus the replay case (the
same envelope reused must not provision a second time -- otherwise "no
signature, no act" degrades into "one signature, act forever").

Every test runs inside a temporary ESTATE_HOME (the `estate_home`
fixture), never the founder's real `~/.estate`, and pins
`SB_TRUST_BACKEND=software_key` so no test prompts Touch ID or reads the
macOS Keychain -- the same isolation sovereign/tests/bdd/conftest.py's
`estate_home` fixture uses, kept local here since this is a plain unit
test file, not a BDD scenario.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from sovereign.engine import ops
from sovereign.engine import paid_compute
from sovereign.trust import approval
from sovereign.trust.anchor import HardwareTrustAnchor


@pytest.fixture
def estate_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "estate"
    (home / "sovereign").mkdir(parents=True)
    monkeypatch.setenv("ESTATE_HOME", str(home))
    monkeypatch.setenv("ESTATE_ENV", str(tmp_path / "absent" / "estate.env"))
    monkeypatch.setenv("ESTATE_SECRETS", str(tmp_path / "absent" / "estate-secrets"))
    monkeypatch.setenv("HOME", str(tmp_path / "fakehome"))
    (tmp_path / "fakehome").mkdir(exist_ok=True)
    monkeypatch.setenv("SB_TRUST_BACKEND", "software_key")
    config = importlib.import_module("sovereign.config")
    importlib.reload(config)
    yield home
    importlib.reload(config)


def test_provision_paid_compute_is_classified_destructive() -> None:
    spec = ops.classify(paid_compute.PROVISION_ACTION)
    assert spec.classification == ops.DESTRUCTIVE
    assert spec.destructive
    assert spec.needs_hardware_signature
    assert spec.needs_quorum


def test_activation_without_a_signature_makes_no_provisioning_call(
    estate_home: Path,
) -> None:
    calls: list[str] = []
    result = paid_compute.activate("rung2", envelope=None, provision=calls.append)
    assert result.ok is False
    assert result.provisioned is False
    assert result.reason == approval.REFUSED_UNSIGNED
    assert calls == [], (
        "the ACCEPT line: no signature must mean no provisioning call, not a refused one"
    )


def test_activation_with_a_hardware_signature_proceeds(estate_home: Path) -> None:
    calls: list[str] = []
    anchor = HardwareTrustAnchor(backend="software_key")
    challenge = approval.challenge(
        "session-cost02", paid_compute.PROVISION_ACTION, "founder"
    )
    envelope = approval.sign(challenge, anchor)

    result = paid_compute.activate("rung2", envelope=envelope, provision=calls.append)

    assert result.ok is True
    assert result.provisioned is True
    assert calls == ["rung2"]
    assert result.attestation is not None
    assert result.counter == int(envelope["counter"])


def test_activation_with_fallback_quorum_proceeds(estate_home: Path) -> None:
    """cp29's degraded-mode contract, reused here: no enclave, so the
    configured multisig set signs instead. 2-of-3 (trust.multisig_threshold)
    is what COST-02's ACCEPT calls "quorum"."""
    calls: list[str] = []
    challenge = approval.challenge(
        "session-cost02", paid_compute.PROVISION_ACTION, "founder"
    )
    envelope = approval.sign_fallback(challenge)

    result = paid_compute.activate("rung2", envelope=envelope, provision=calls.append)

    assert result.ok is True
    assert result.provisioned is True
    assert calls == ["rung2"]


def test_a_single_fallback_signer_short_of_quorum_is_refused(estate_home: Path) -> None:
    calls: list[str] = []
    challenge = approval.challenge(
        "session-cost02", paid_compute.PROVISION_ACTION, "founder"
    )
    full = approval.sign_fallback(challenge)
    one_signer = {list(full["signers"].keys())[0]: list(full["signers"].values())[0]}
    envelope = {**full, "signers": one_signer}

    result = paid_compute.activate("rung2", envelope=envelope, provision=calls.append)

    assert result.ok is False
    assert result.reason == approval.REFUSED_QUORUM
    assert calls == []


def test_a_replayed_envelope_provisions_nothing_the_second_time(
    estate_home: Path,
) -> None:
    calls: list[str] = []
    anchor = HardwareTrustAnchor(backend="software_key")
    challenge = approval.challenge(
        "session-cost02", paid_compute.PROVISION_ACTION, "founder"
    )
    envelope = approval.sign(challenge, anchor)

    first = paid_compute.activate("rung2", envelope=envelope, provision=calls.append)
    second = paid_compute.activate("rung2", envelope=envelope, provision=calls.append)

    assert first.ok is True and first.provisioned is True
    assert second.ok is False
    assert second.reason == approval.REFUSED_REPLAY
    assert calls == ["rung2"], "the replay must not provision a second time"

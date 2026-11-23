"""E1-E4 is enforced at the existing Greenlane OPERATIONAL verdict, not Hermes.

Synthetic keys and signed receipts below prove the gate logic, not physical
independence or a live production effect. Actual custodian receipts remain required.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from greenlane import github as G
from lib.epistemic_kernel import (
    EvidenceTier,
    ExecutionPlane,
    SignedReceipt,
    canonical_json,
    sign_receipt,
)


REV = "a" * 40
URL = "https://production.example.test/health"
NEEDLE = "service-ready"


def _setup(monkeypatch, *, same_keys=False, bad_quad=False, expired=False):
    now = datetime.now(timezone.utc)
    keys = {
        "observer-oci": b"oci-isolated-evidence-key-for-tests",
        "observer-edge": b"edge-isolated-evidence-key-for-tests",
        "observer-remote": b"remote-isolated-evidence-key-tests",
    }
    if same_keys:
        keys["observer-remote"] = keys["observer-oci"]
    quad_key = b"independently-owned-quad-custody-key"
    attestation = {
        "revision": REV,
        "target": URL,
        "expires_at": (
            now - timedelta(minutes=1) if expired else now + timedelta(minutes=30)
        ).isoformat(),
        "authorities": {
            "observer-oci": {"principal": "oci-read-only", "control_plane": "oci"},
            "observer-edge": {"principal": "cloudflare-prober", "control_plane": "edge"},
            "observer-remote": {
                "principal": "remote-third-party",
                "control_plane": "independent",
            },
        },
    }
    signature = hmac.new(
        quad_key, canonical_json(attestation).encode(), hashlib.sha256
    ).hexdigest()
    if bad_quad:
        signature = "0" * len(signature)
    monkeypatch.setenv(
        "EPISTEMIC_AUTHORITY_KEYS_JSON",
        json.dumps({name: key.hex() for name, key in keys.items()}),
    )
    monkeypatch.setenv("EPISTEMIC_QUAD_KEY_HEX", quad_key.hex())
    monkeypatch.setenv(
        "EPISTEMIC_QUAD_CUSTODY_JSON",
        json.dumps({"payload": attestation, "signature": signature}),
    )
    monkeypatch.setenv("EPISTEMIC_MIN_FENCE", "7")

    raw = json.dumps({"status": "ok", "commit_sha": REV, "service": NEEDLE})
    receipts = []
    for i, (authority, key) in enumerate(keys.items()):
        receipt = SignedReceipt(
            receipt_id=f"isolated-{i}",
            tier=EvidenceTier.TIER_0_RAW_MACHINE_RECEIPT.value,
            plane=ExecutionPlane.PLANE_PRODUCTION_RUNTIME.value,
            capture_authority=authority,
            subject_agent_id="untrusted-worker",
            observer_scope="provider_account",
            target_uri=URL,
            observed_at_utc=now.isoformat(),
            fencing_token=7,
            exit_code=0,
            http_status=200,
            raw_payload=raw,
            raw_payload_sha256=hashlib.sha256(raw.encode()).hexdigest(),
        )
        receipts.append(asdict(sign_receipt(receipt, key)))
    return {"tip": REV, "epistemic_receipts": receipts}


def test_source_plane_can_never_claim_operational_even_when_get_200(monkeypatch):
    backend = G.GitHubBackend.__new__(G.GitHubBackend)
    backend._claim_of = lambda _: ("chidionyema/idp", "8415")
    backend._contract = lambda *_: {
        "accept": (
            "GET https://raw.githubusercontent.com/chidionyema/idp/main/greenlane/"
            "github.py expect 200 contains \"verify_operational\" within 180m"
        ),
        "optimus": "claims.ship_contract_enforced baseline=UNKNOWN target=1",
    }
    backend._optimus_readings = lambda _: {"claims.ship_contract_enforced": 1.0}
    monkeypatch.setattr(G, "_http_get", lambda *_: (200, "verify_operational"))
    verdict, reason = backend.verify_operational("lane/source-only", {"tip": REV})
    assert verdict == "pending"
    assert "ERR_PROXY_GREEN_SUBSTITUTION" in reason


def test_empty_producer_receipts_deny(monkeypatch):
    _setup(monkeypatch)
    reason = G.GitHubBackend._epistemic_operational_proof(
        {"tip": REV}, URL, 200, NEEDLE
    )
    assert "ERR_INSUFFICIENT_RUNTIME_PROOFS" in reason


def test_missing_verifier_key_custody_deny(monkeypatch):
    rec = _setup(monkeypatch)
    monkeypatch.delenv("EPISTEMIC_QUAD_KEY_HEX")
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "ERR_INDEPENDENT_KEY_CUSTODY_NOT_PROVEN" in reason


def test_shared_authority_keys_deny(monkeypatch):
    rec = _setup(monkeypatch, same_keys=True)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "ERR_INDEPENDENT_KEY_CUSTODY_NOT_PROVEN" in reason


def test_bad_quad_signature_deny(monkeypatch):
    rec = _setup(monkeypatch, bad_quad=True)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert reason == "ERR_QUAD_CUSTODY_SIGNATURE"


def test_expired_quad_signature_deny(monkeypatch):
    rec = _setup(monkeypatch, expired=True)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert reason == "ERR_QUAD_CUSTODY_EXPIRED"


def test_wrong_production_revision_deny(monkeypatch):
    rec = _setup(monkeypatch)
    rec["tip"] = "b" * 40
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert reason == "ERR_QUAD_CUSTODY_BINDING"


def test_tampered_production_receipt_deny(monkeypatch):
    rec = _setup(monkeypatch)
    rec["epistemic_receipts"][0]["raw_payload"] = "forged success"
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "ERR_PAYLOAD_TAMPERED" in reason


def test_duplicate_production_receipt_deny(monkeypatch):
    rec = _setup(monkeypatch)
    rec["epistemic_receipts"][2] = rec["epistemic_receipts"][1]
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE)
    assert "ERR_DUPLICATE_OR_EMPTY_RECEIPT_ID" in reason


def test_independently_signed_fresh_matching_receipts_satisfy_verifier(
    monkeypatch,
):
    rec = _setup(monkeypatch)
    assert G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, NEEDLE) == ""


def test_no_body_invariant_cannot_settle(monkeypatch):
    rec = _setup(monkeypatch)
    reason = G.GitHubBackend._epistemic_operational_proof(rec, URL, 200, None)
    assert "ERR_INVALID_OPERATIONAL_CONTRACT" in reason

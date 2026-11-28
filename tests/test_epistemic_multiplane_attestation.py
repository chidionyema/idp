"""Falsifiers for multi-plane asymmetric QUAD + SPIFFE + OIDC epistemic attestation (idp#8759, D11)."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOD_PATH = ROOT / "platform" / "estate" / "epistemic" / "attest.py"

_spec = importlib.util.spec_from_file_location("epistemic_attest", MOD_PATH)
assert _spec and _spec.loader
attest = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = attest
_spec.loader.exec_module(attest)

NOW = datetime(2026, 11, 28, 18, 0, 0, tzinfo=timezone.utc)
ISSUED = "2026-11-28T17:55:00Z"
EXPIRES = "2026-11-28T18:10:00Z"
REV = "6d59dacbac7e1111222233334444555566667777"
TARGET = "https://live.meridianlabs.cloud/health"
BODY_SHA = hashlib.sha256(b'{"ok":true,"schema":"estate-live-state.v1"}').hexdigest()


def _valid_fixture():
    priv_gh, pub_gh = attest.generate_ed25519_keypair()
    priv_sp, pub_sp = attest.generate_ed25519_keypair()
    priv_ed, pub_ed = attest.generate_ed25519_keypair()

    policy = {
        "gh-landed": attest.TrustAuthority(
            name="gh-landed",
            principal="github-actions/greenlane",
            control_plane="github-oidc",
            proof_kind="sigstore-oidc",
            public_key_pem=pub_gh,
            oidc_issuer="https://token.actions.githubusercontent.com",
        ),
        "spire-running": attest.TrustAuthority(
            name="spire-running",
            principal="workload/estate-live-state",
            control_plane="spire-arm-node",
            proof_kind="spiffe-svid",
            public_key_pem=pub_sp,
            spiffe_id="spiffe://estate.internal/ns/estate/sa/live-state",
        ),
        "edge-observed": attest.TrustAuthority(
            name="edge-observed",
            principal="prober/tempo-quorum",
            control_plane="zone-b-cloudflare-edge",
            proof_kind="ed25519",
            public_key_pem=pub_ed,
        ),
    }

    bundle = [
        attest.make_attestation(
            authority="gh-landed",
            role="landed",
            proof_kind="sigstore-oidc",
            revision=REV,
            target_url=TARGET,
            http_status=200,
            body_sha256=BODY_SHA,
            fencing_token=10,
            issued_at=ISSUED,
            expires_at=EXPIRES,
            private_pem=priv_gh,
            oidc_issuer="https://token.actions.githubusercontent.com",
            rekor_log_index=4159540474,
        ),
        attest.make_attestation(
            authority="spire-running",
            role="running",
            proof_kind="spiffe-svid",
            revision=REV,
            target_url=TARGET,
            http_status=200,
            body_sha256=BODY_SHA,
            fencing_token=10,
            issued_at=ISSUED,
            expires_at=EXPIRES,
            private_pem=priv_sp,
            spiffe_id="spiffe://estate.internal/ns/estate/sa/live-state",
        ),
        attest.make_attestation(
            authority="edge-observed",
            role="observed",
            proof_kind="ed25519",
            revision=REV,
            target_url=TARGET,
            http_status=200,
            body_sha256=BODY_SHA,
            fencing_token=10,
            issued_at=ISSUED,
            expires_at=EXPIRES,
            private_pem=priv_ed,
        ),
    ]
    return policy, bundle, (priv_gh, priv_sp, priv_ed)


def test_three_independent_asymmetric_planes_pass_with_zero_verifier_secrets():
    policy, bundle, _ = _valid_fixture()
    verdict = attest.verify_multiplane_bundle(
        attestations=bundle,
        trust_policy=policy,
        expected_revision=REV,
        expected_target_url=TARGET,
        now=NOW,
        is_spiffe_revoked=lambda _sid: False,
    )
    assert verdict.allowed is True, verdict.error_codes
    assert verdict.verified_authorities == (
        "gh-landed",
        "spire-running",
        "edge-observed",
    )


def test_falsifier_rejects_tampered_signature():
    policy, bundle, _ = _valid_fixture()
    bundle[2]["payload"]["http_status"] = 200
    bundle[2]["payload"]["fencing_token"] = 11  # mutate signed payload
    verdict = attest.verify_multiplane_bundle(
        attestations=bundle,
        trust_policy=policy,
        expected_revision=REV,
        expected_target_url=TARGET,
        now=NOW,
    )
    assert verdict.allowed is False
    assert any("ERR_INVALID_SIGNATURE" in c for c in verdict.error_codes)


def test_falsifier_rejects_revoked_spiffe_svid_ghost_agent():
    policy, bundle, _ = _valid_fixture()
    verdict = attest.verify_multiplane_bundle(
        attestations=bundle,
        trust_policy=policy,
        expected_revision=REV,
        expected_target_url=TARGET,
        now=NOW,
        is_spiffe_revoked=lambda sid: sid.endswith("/live-state"),
    )
    assert verdict.allowed is False
    assert any("ERR_SPIFFE_SVID_REVOKED" in c for c in verdict.error_codes)


def test_falsifier_rejects_shared_control_plane_collusion():
    policy, bundle, _ = _valid_fixture()
    # Two authorities on the same control plane violate QUAD isolation
    policy["edge-observed"] = attest.TrustAuthority(
        name="edge-observed",
        principal="prober/tempo-quorum",
        control_plane="github-oidc",
        proof_kind="ed25519",
        public_key_pem=policy["edge-observed"].public_key_pem,
    )
    verdict = attest.verify_multiplane_bundle(
        attestations=bundle,
        trust_policy=policy,
        expected_revision=REV,
        expected_target_url=TARGET,
        now=NOW,
    )
    assert verdict.allowed is False
    assert any("ERR_QUAD_CUSTODY_NOT_ISOLATED" in c for c in verdict.error_codes)


def test_falsifier_rejects_symmetric_hmac_and_proxy_github_target():
    policy, bundle, _ = _valid_fixture()
    bundle[0]["payload"]["proof_kind"] = "hmac"
    v_hmac = attest.verify_multiplane_bundle(
        attestations=bundle,
        trust_policy=policy,
        expected_revision=REV,
        expected_target_url=TARGET,
        now=NOW,
    )
    assert v_hmac.allowed is False
    assert "ERR_SYMMETRIC_OR_UNSUPPORTED_PROOF_KIND" in v_hmac.error_codes

    policy2, bundle2, _ = _valid_fixture()
    v_proxy = attest.verify_multiplane_bundle(
        attestations=bundle2,
        trust_policy=policy2,
        expected_revision=REV,
        expected_target_url="https://raw.githubusercontent.com/chidionyema/idp/main/README.md",
        now=NOW,
    )
    assert v_proxy.allowed is False
    assert v_proxy.error_codes == ("ERR_PROXY_GREEN_SUBSTITUTION",)


def test_falsifier_rejects_expired_attestation_and_dev_spiffe_fallback():
    policy, bundle, (_, priv_sp, _) = _valid_fixture()
    v_exp = attest.verify_multiplane_bundle(
        attestations=bundle,
        trust_policy=policy,
        expected_revision=REV,
        expected_target_url=TARGET,
        now=datetime(2026, 11, 28, 18, 15, 0, tzinfo=timezone.utc),
    )
    assert v_exp.allowed is False
    assert any("ERR_ATTESTATION_EXPIRED" in c for c in v_exp.error_codes)

    # Dev fallback SPIFFE ID (/dev/...) must never pass as attested
    dev_sid = "spiffe://estate.internal/dev/roseonyema/mac"
    policy["spire-running"] = attest.TrustAuthority(
        name="spire-running",
        principal="workload/dev",
        control_plane="spire-arm-node",
        proof_kind="spiffe-svid",
        public_key_pem=policy["spire-running"].public_key_pem,
        spiffe_id=dev_sid,
    )
    bundle[1] = attest.make_attestation(
        authority="spire-running",
        role="running",
        proof_kind="spiffe-svid",
        revision=REV,
        target_url=TARGET,
        http_status=200,
        body_sha256=BODY_SHA,
        fencing_token=10,
        issued_at=ISSUED,
        expires_at=EXPIRES,
        private_pem=priv_sp,
        spiffe_id=dev_sid,
    )
    v_dev = attest.verify_multiplane_bundle(
        attestations=bundle,
        trust_policy=policy,
        expected_revision=REV,
        expected_target_url=TARGET,
        now=NOW,
    )
    assert v_dev.allowed is False
    assert any("ERR_SPIFFE_DEV_FALLBACK_NOT_ATTESTED" in c for c in v_dev.error_codes)

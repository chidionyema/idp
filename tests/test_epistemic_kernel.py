"""Adversarial 18-case test suite + cross-language canonical vector verification.

Replays every structural failure observed during the Nov 22-23 router-edge incident:
  - Epistemic laundering of router-edge-repair-evidence.json (TIER_2 -> TIER_0)
  - Empty job_env variable promoted to estate_global secret non-existence
  - Issue #8485 raw.githubusercontent.com 200 stamping OPERATIONAL during HTTP 525
  - Self-signed agent forgery, stdout tampering, stale fence, expired TTL, confirmation bias
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from epistemic_kernel import (
    EpistemicKernel,
    EvidenceTier,
    ExecutionPlane,
    SignedReceipt,
    canonical_json,
    sign_receipt,
)
from epistemic_kernel.kernel import sha256_hex

TEST_KEY = b"isolated-verifier-key-never-exposed-to-agent-32b"
TRUSTED = ("gh-actions-prober", "cloudflare-prober", "oci-blackbox-prober")
NOW = datetime(2026, 11, 23, 18, 50, 0, tzinfo=timezone.utc)


def make_receipt(
    receipt_id: str = "rcpt-1",
    tier: str = EvidenceTier.TIER_0_RAW_MACHINE_RECEIPT.value,
    plane: str = ExecutionPlane.PLANE_PRODUCTION_RUNTIME.value,
    capture_authority: str = "oci-blackbox-prober",
    subject_agent_id: str = "legion-agent-8416",
    observer_scope: str = "job_env",
    target_uri: str = "https://llm.meridianlabs.cloud/health",
    observed_at_utc: str = "2026-11-23T18:45:00Z",
    fencing_token: int = 10,
    exit_code: int = 0,
    http_status: int | None = 200,
    raw_payload: str = '{"status":"ok","edge":"zone-b-cloudflare-edge"}',
    sign: bool = True,
) -> SignedReceipt:
    r = SignedReceipt(
        receipt_id=receipt_id,
        tier=tier,
        plane=plane,
        capture_authority=capture_authority,
        subject_agent_id=subject_agent_id,
        observer_scope=observer_scope,
        target_uri=target_uri,
        observed_at_utc=observed_at_utc,
        fencing_token=fencing_token,
        exit_code=exit_code,
        http_status=http_status,
        raw_payload=raw_payload,
        raw_payload_sha256=sha256_hex(raw_payload),
    )
    return sign_receipt(r, TEST_KEY) if sign else r


class TestEpistemicFalsificationKernel(unittest.TestCase):
    def setUp(self) -> None:
        self.kernel = EpistemicKernel(TEST_KEY, TRUSTED, max_receipt_age_seconds=3600)

    # --- E1: Anti-Epistemic-Laundering ---
    def test_01_blocks_tier2_drive_json_laundered_as_primary_fact(self) -> None:
        r = make_receipt(receipt_id="rcpt-job", observer_scope="job_env", plane=ExecutionPlane.PLANE_CI_BUILD.value, http_status=None, raw_payload="SEED_CLOUDFLARE_WORKERS_TOKEN=")
        envelope = {
            "mission_id": "idp#8416",
            "cited_sources": [{"source_id": "router-edge-repair-evidence.json", "tier": "TIER_2_AGENT_INFERENCE", "used_as_primary_fact": True}],
            "observed_facts": [{"statement": "env var empty in job", "receipt_id": "rcpt-job"}],
            "competing_hypotheses": [
                {"id": "H1", "statement": "delivery defect", "falsified_by": "non-empty secret in job", "discriminating_probe": "inspect workflow env"},
                {"id": "H2", "statement": "secret missing", "falsified_by": "vault read returns secret", "discriminating_probe": "query vault"},
            ],
            "promoted_claims": [],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_EPISTEMIC_LAUNDERING_BLOCKED", d.error_codes)

    def test_02_blocks_tier2_receipt_even_if_hmac_signed(self) -> None:
        r = make_receipt(receipt_id="rcpt-t2", tier=EvidenceTier.TIER_2_AGENT_INFERENCE.value)
        envelope = {
            "mission_id": "idp#8416",
            "observed_facts": [{"statement": "agent says missing", "receipt_id": "rcpt-t2"}],
            "competing_hypotheses": [
                {"id": "H1", "statement": "a", "falsified_by": "x", "discriminating_probe": "p1"},
                {"id": "H2", "statement": "b", "falsified_by": "y", "discriminating_probe": "p2"},
            ],
            "promoted_claims": [],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertTrue(any("ERR_EPISTEMIC_LAUNDERING_BLOCKED" in c for c in d.error_codes))

    # --- E2: Scope-Bounded Negation & Mandatory Falsification ---
    def test_03_blocks_empty_job_env_promoted_to_estate_global_nonexistence(self) -> None:
        r = make_receipt(
            receipt_id="rcpt-empty-env",
            plane=ExecutionPlane.PLANE_CI_BUILD.value,
            observer_scope="job_env",
            target_uri="https://github.com/chidionyema/idp/actions/runs/999",
            http_status=None,
            raw_payload="SEED_CLOUDFLARE_WORKERS_TOKEN=<empty>",
        )
        envelope = {
            "mission_id": "idp#8416",
            "observed_facts": [{"statement": "release job saw empty var", "receipt_id": "rcpt-empty-env"}],
            "competing_hypotheses": [
                {"id": "H1", "statement": "credential delivery defect in release workflow", "falsified_by": "workflow binds right env+vault", "discriminating_probe": "inspect workflow yaml"},
                {"id": "H2", "statement": "credentials absent from estate", "falsified_by": "OCI vault returns active token", "discriminating_probe": "run vault lookup"},
            ],
            "promoted_claims": [
                {
                    "id": "C1",
                    "claim_type": "existential_negation",
                    "claim_scope": "estate_global",
                    "supporting_receipt_ids": ["rcpt-empty-env"],
                }
            ],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_INVALID_NEGATION_SCOPE_LEAP", d.error_codes)

    def test_04_accepts_properly_scoped_job_env_claim_with_dual_hypotheses(self) -> None:
        r = make_receipt(
            receipt_id="rcpt-empty-env",
            plane=ExecutionPlane.PLANE_CI_BUILD.value,
            observer_scope="job_env",
            target_uri="https://github.com/chidionyema/idp/actions/runs/999",
            http_status=None,
            raw_payload="SEED_CLOUDFLARE_WORKERS_TOKEN=<empty>",
        )
        envelope = {
            "mission_id": "idp#8416",
            "observed_facts": [{"statement": "release job saw empty var", "receipt_id": "rcpt-empty-env"}],
            "competing_hypotheses": [
                {"id": "H1", "statement": "credential delivery defect", "falsified_by": "job receives populated env", "discriminating_probe": "audit workflow environment binding"},
                {"id": "H2", "statement": "credential absent in store", "falsified_by": "OCI vault verifies token", "discriminating_probe": "run vault existence check"},
            ],
            "promoted_claims": [
                {
                    "id": "C1",
                    "claim_type": "existential_negation",
                    "claim_scope": "job_env",
                    "supporting_receipt_ids": ["rcpt-empty-env"],
                }
            ],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r], now_utc=NOW)
        self.assertTrue(d.allowed, d.error_codes)
        self.assertEqual(d.verdict, "VERIFIED_DIAGNOSIS_PENDING_DISCRIMINATOR")
        self.assertEqual(d.operational_yield, 0)

    def test_05_allows_estate_global_negation_only_when_all_three_stores_proved(self) -> None:
        r1 = make_receipt(receipt_id="r-repo", observer_scope="repo_secrets", plane=ExecutionPlane.PLANE_CONTROL_AUTH.value, http_status=404, raw_payload="not found")
        r2 = make_receipt(receipt_id="r-vault", observer_scope="vault_store", plane=ExecutionPlane.PLANE_CONTROL_AUTH.value, http_status=404, raw_payload="not found")
        r3 = make_receipt(receipt_id="r-cf", observer_scope="provider_account", plane=ExecutionPlane.PLANE_CONTROL_AUTH.value, http_status=404, raw_payload="not found")
        envelope = {
            "mission_id": "idp#8416",
            "observed_facts": [
                {"statement": "absent in repo secrets", "receipt_id": "r-repo"},
                {"statement": "absent in vault", "receipt_id": "r-vault"},
                {"statement": "absent in cloudflare", "receipt_id": "r-cf"},
            ],
            "competing_hypotheses": [
                {"id": "H1", "statement": "never provisioned", "falsified_by": "audit log creation entry", "discriminating_probe": "check audit log"},
                {"id": "H2", "statement": "revoked/deleted", "falsified_by": "no delete event", "discriminating_probe": "check delete log"},
            ],
            "promoted_claims": [
                {
                    "id": "C-global",
                    "claim_type": "existential_negation",
                    "claim_scope": "estate_global",
                    "supporting_receipt_ids": ["r-repo", "r-vault", "r-cf"],
                }
            ],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r1, r2, r3], now_utc=NOW)
        self.assertTrue(d.allowed, d.error_codes)

    def test_06_blocks_single_hypothesis_confirmation_bias(self) -> None:
        r = make_receipt(receipt_id="r1", observer_scope="job_env", plane=ExecutionPlane.PLANE_CI_BUILD.value)
        envelope = {
            "mission_id": "idp#8416",
            "observed_facts": [{"statement": "var empty", "receipt_id": "r1"}],
            "competing_hypotheses": [
                {"id": "H1", "statement": "token missing", "falsified_by": "found", "discriminating_probe": "check"},
            ],
            "promoted_claims": [],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_CONFIRMATION_BIAS_NO_ALTERNATIVE", d.error_codes)

    def test_07_blocks_unfalsifiable_hypothesis_missing_discriminator(self) -> None:
        r = make_receipt(receipt_id="r1", observer_scope="job_env", plane=ExecutionPlane.PLANE_CI_BUILD.value)
        envelope = {
            "mission_id": "idp#8416",
            "observed_facts": [{"statement": "var empty", "receipt_id": "r1"}],
            "competing_hypotheses": [
                {"id": "H1", "statement": "a", "falsified_by": "", "discriminating_probe": "p1"},
                {"id": "H2", "statement": "b", "falsified_by": "x", "discriminating_probe": ""},
            ],
            "promoted_claims": [],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_UNFALSIFIABLE_HYPOTHESIS:0", d.error_codes)
        self.assertIn("ERR_UNFALSIFIABLE_HYPOTHESIS:1", d.error_codes)

    def test_08_blocks_premature_mutating_remediation_before_discrimination(self) -> None:
        r = make_receipt(receipt_id="r1", observer_scope="job_env", plane=ExecutionPlane.PLANE_CI_BUILD.value)
        envelope = {
            "mission_id": "idp#8416",
            "requests_mutation": True,
            "observed_facts": [{"statement": "var empty", "receipt_id": "r1"}],
            "competing_hypotheses": [
                {"id": "H1", "statement": "delivery defect", "falsified_by": "x", "discriminating_probe": "p1", "status": "OPEN"},
                {"id": "H2", "statement": "missing secret", "falsified_by": "y", "discriminating_probe": "p2", "status": "OPEN"},
            ],
            "promoted_claims": [],
        }
        d = self.kernel.evaluate_diagnosis(envelope, [r], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_PREMATURE_MUTATION_BEFORE_DISCRIMINATION", d.error_codes)

    # --- E3: Anti-Proxy-Green Runtime Contract Binding ---
    def test_09_blocks_issue_8485_raw_githubusercontent_proxy_green(self) -> None:
        proxy_receipt = make_receipt(
            receipt_id="rcpt-8485-proxy",
            plane=ExecutionPlane.PLANE_PRODUCTION_RUNTIME.value,  # Even if bot lies about plane!
            target_uri="https://raw.githubusercontent.com/chidionyema/idp/main/platform/llm/router_catalog.py",
            http_status=200,
            raw_payload="# router_catalog.py zone-b-cloudflare-edge",
        )
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [proxy_receipt], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertEqual(d.operational_yield, 0)
        self.assertIn("ERR_PROXY_GREEN_SUBSTITUTION:rcpt-8485-proxy", d.error_codes)

    def test_10_blocks_http_525_edge_ssl_handshake_failure(self) -> None:
        r525 = make_receipt(
            receipt_id="rcpt-525",
            plane=ExecutionPlane.PLANE_PRODUCTION_RUNTIME.value,
            target_uri="https://llm.meridianlabs.cloud/health",
            http_status=525,
            raw_payload="SSL handshake failed",
        )
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [r525], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertEqual(d.operational_yield, 0)
        self.assertIn("ERR_RUNTIME_STATUS_MISMATCH:rcpt-525:got_525_want_200", d.error_codes)

    def test_11_blocks_200_missing_body_invariant(self) -> None:
        r200_bad = make_receipt(
            receipt_id="rcpt-bad-body",
            plane=ExecutionPlane.PLANE_PRODUCTION_RUNTIME.value,
            target_uri="https://llm.meridianlabs.cloud/health",
            http_status=200,
            raw_payload='{"status":"ok","edge":"legacy-placeholder"}',
        )
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [r200_bad], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_RUNTIME_INVARIANT_MISSING:rcpt-bad-body", d.error_codes)

    def test_12_accepts_3_converging_production_runtime_proofs(self) -> None:
        receipts = [
            make_receipt(receipt_id="p1", capture_authority="oci-blackbox-prober"),
            make_receipt(receipt_id="p2", capture_authority="cloudflare-prober"),
            make_receipt(receipt_id="p3", capture_authority="gh-actions-prober"),
        ]
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 3,
        }
        # Existing v1 fake independence (one shared HMAC secret) must NOT pass.
        d = self.kernel.evaluate_operational_transition(contract, receipts, now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_INDEPENDENT_KEY_CUSTODY_NOT_PROVEN", d.error_codes)
        distinct_keys = {a: ("separate-signer-" + a).encode() for a in TRUSTED}
        receipts = [sign_receipt(make_receipt(receipt_id="g-"+a, capture_authority=a, sign=False), distinct_keys[a]) for a in TRUSTED]
        trusted_kernel = EpistemicKernel(TEST_KEY, TRUSTED, authority_keys=distinct_keys)
        d = trusted_kernel.evaluate_operational_transition(contract, receipts, now_utc=NOW)
        self.assertTrue(d.allowed, d.error_codes)
        self.assertEqual(d.verdict, "VERIFIED_OPERATIONAL_YIELD")
        self.assertEqual(d.operational_yield, 1)
        self.assertEqual(len(d.verified_receipt_ids), 3)

    # --- E4: Cryptographic Isolation, Tamper, Replay & TTL Defenses ---
    def test_13_blocks_self_signed_agent_receipt(self) -> None:
        forged = make_receipt(
            receipt_id="rcpt-self",
            capture_authority="oci-blackbox-prober",
            subject_agent_id="oci-blackbox-prober",
        )
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [forged], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("rcpt-self:ERR_FORGED_OR_SELF_SIGNED_RECEIPT", d.error_codes)

    def test_14_blocks_tampered_stdout_payload_after_signing(self) -> None:
        valid = make_receipt(receipt_id="rcpt-tamper")
        tampered = SignedReceipt(**{**valid.__dict__, "raw_payload": '{"status":"forged","edge":"zone-b-cloudflare-edge"}'})
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [tampered], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("rcpt-tamper:ERR_PAYLOAD_TAMPERED", d.error_codes)

    def test_15_blocks_tampered_metadata_http_status_after_signing(self) -> None:
        valid = make_receipt(receipt_id="rcpt-meta", http_status=525)
        tampered = SignedReceipt(**{**valid.__dict__, "http_status": 200})
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [tampered], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("rcpt-meta:ERR_SIGNATURE_MISMATCH", d.error_codes)

    def test_16_blocks_stale_fencing_token_zombie_replay(self) -> None:
        stale = make_receipt(receipt_id="rcpt-zombie", fencing_token=4)
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [stale], now_utc=NOW, min_fencing_token=10)
        self.assertFalse(d.allowed)
        self.assertIn("rcpt-zombie:ERR_STALE_FENCING_TOKEN", d.error_codes)

    def test_17_blocks_expired_stale_receipt_ttl(self) -> None:
        old = make_receipt(receipt_id="rcpt-old", observed_at_utc="2026-11-22T10:00:00Z")
        contract = {
            "expected_host": "llm.meridianlabs.cloud",
            "expected_path": "/health",
            "expected_http_status": 200,
            "expected_body_contains": "zone-b-cloudflare-edge",
            "min_independent_proofs": 1,
        }
        d = self.kernel.evaluate_operational_transition(contract, [old], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("rcpt-old:ERR_STALE_RECEIPT", d.error_codes)

    def test_18_cli_gate_fail_closed_and_pass_exit_codes(self) -> None:
        cli_path = Path(__file__).resolve().parent.parent / "bin" / "epistemic_gate.py"
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            contract_file = td_path / "contract.json"
            receipts_bad = td_path / "bad.json"
            receipts_good = td_path / "good.json"

            contract_file.write_text(json.dumps({
                "expected_host": "llm.meridianlabs.cloud",
                "expected_path": "/health",
                "expected_http_status": 200,
                "expected_body_contains": "zone-b-cloudflare-edge",
                "min_independent_proofs": 1,
            }), encoding="utf-8")

            bad = make_receipt(
                receipt_id="cli-bad",
                target_uri="https://raw.githubusercontent.com/chidionyema/idp/main/x.py",
                observed_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            good = make_receipt(
                receipt_id="cli-good",
                target_uri="https://llm.meridianlabs.cloud/health",
                observed_at_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
            receipts_bad.write_text(json.dumps([bad.__dict__]), encoding="utf-8")
            receipts_good.write_text(json.dumps([good.__dict__]), encoding="utf-8")

            env = {
                "PATH": "/usr/bin:/bin",
                "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "lib"),
                "ESTATE_RECEIPT_KEY": TEST_KEY.decode("utf-8"),
            }
            p_bad = subprocess.run(
                [sys.executable, str(cli_path), "--mode", "operational", "--input", str(contract_file), "--receipts", str(receipts_bad)],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(p_bad.returncode, 42, p_bad.stdout + p_bad.stderr)

            p_good = subprocess.run(
                [sys.executable, str(cli_path), "--mode", "operational", "--input", str(contract_file), "--receipts", str(receipts_good)],
                capture_output=True, text=True, env=env,
            )
            self.assertEqual(p_good.returncode, 0, p_good.stdout + p_good.stderr)


    # New independent negative acceptance tests: fail closed against false yield.
    def test_19_rejects_empty_operational_contract(self):
        r = make_receipt()
        d = self.kernel.evaluate_operational_transition({}, [r], now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_INVALID_OPERATIONAL_CONTRACT", d.error_codes)

    def test_20_rejects_correlated_signed_receipts_with_one_authority(self):
        receipts = [make_receipt(receipt_id=f"same-authority-{n}") for n in range(3)]
        contract = {"expected_host": "llm.meridianlabs.cloud", "expected_path": "/health",
                    "expected_http_status": 200, "expected_body_contains": "zone-b-cloudflare-edge", "min_independent_proofs": 3}
        d = self.kernel.evaluate_operational_transition(contract, receipts, now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_INSUFFICIENT_INDEPENDENT_AUTHORITIES:got_1_want_3", d.error_codes)

    def test_21_rejects_three_authority_labels_signed_with_shared_key(self):
        receipts = [make_receipt(receipt_id=f"unisolated-{n}", capture_authority=a) for n, a in enumerate(TRUSTED)]
        contract = {"expected_host": "llm.meridianlabs.cloud", "expected_path": "/health",
                    "expected_http_status": 200, "expected_body_contains": "zone-b-cloudflare-edge", "min_independent_proofs": 3}
        d = self.kernel.evaluate_operational_transition(contract, receipts, now_utc=NOW)
        self.assertFalse(d.allowed)
        self.assertIn("ERR_INDEPENDENT_KEY_CUSTODY_NOT_PROVEN", d.error_codes)

    def test_22_rejects_http_runtime_receipts(self):
        r = make_receipt(target_uri="http://llm.meridianlabs.cloud/health")
        c = {"expected_host": "llm.meridianlabs.cloud", "expected_path": "/health",
             "expected_http_status": 200, "expected_body_contains": "zone-b-cloudflare-edge", "min_independent_proofs": 1}
        d = self.kernel.evaluate_operational_transition(c, [r], now_utc=NOW)
        self.assertIn("ERR_INVALID_RUNTIME_TARGET:rcpt-1", d.error_codes)

    def test_23_rejects_tier1_operational_receipt_even_if_signed(self):
        r = make_receipt(tier=EvidenceTier.TIER_1_CORROBORATED_OBSERVATION.value)
        c = {"expected_host": "llm.meridianlabs.cloud", "expected_path": "/health",
             "expected_http_status": 200, "expected_body_contains": "zone-b-cloudflare-edge", "min_independent_proofs": 1}
        d = self.kernel.evaluate_operational_transition(c, [r], now_utc=NOW)
        self.assertIn("ERR_NON_PRIMARY_OR_FAILED_PROBE:rcpt-1", d.error_codes)

    def test_24_rejects_success_http_if_probe_process_failed(self):
        r = make_receipt(exit_code=1)
        c = {"expected_host": "llm.meridianlabs.cloud", "expected_path": "/health",
             "expected_http_status": 200, "expected_body_contains": "zone-b-cloudflare-edge", "min_independent_proofs": 1}
        d = self.kernel.evaluate_operational_transition(c, [r], now_utc=NOW)
        self.assertIn("ERR_NON_PRIMARY_OR_FAILED_PROBE:rcpt-1", d.error_codes)

    def test_25_rejects_duplicate_receipt_ids(self):
        a = make_receipt(receipt_id="replay")
        b = make_receipt(receipt_id="replay")
        c = {"expected_host": "llm.meridianlabs.cloud", "expected_path": "/health",
             "expected_http_status": 200, "expected_body_contains": "zone-b-cloudflare-edge", "min_independent_proofs": 1}
        d = self.kernel.evaluate_operational_transition(c, [a,b], now_utc=NOW)
        self.assertIn("replay:ERR_DUPLICATE_OR_EMPTY_RECEIPT_ID", d.error_codes)

    def test_26_remediation_cannot_self_assert_read_only_to_bypass_falsifier(self):
        r = make_receipt(plane=ExecutionPlane.PLANE_CI_BUILD.value)
        e = {"observed_facts":[{"statement":"one run","receipt_id":"rcpt-1"}],
             "requests_mutation":True,"mutation_is_read_only_probe":True,
             "competing_hypotheses":[
                {"id":"H1","statement":"delivery","falsified_by":"store proof","discriminating_probe":"read store"},
                {"id":"H2","statement":"absent","falsified_by":"token found","discriminating_probe":"read token"}]}
        d = self.kernel.evaluate_diagnosis(e,[r],now_utc=NOW)
        self.assertIn("ERR_PREMATURE_MUTATION_BEFORE_DISCRIMINATION", d.error_codes)

    def test_27_rejects_wrong_exact_revision_even_if_body_contains_expected_service(self):
        r = make_receipt(raw_payload='{"status":"ok","edge":"zone-b-cloudflare-edge","commit_sha":"' + "a"*40 + '"}')
        c = {"expected_host":"llm.meridianlabs.cloud","expected_path":"/health", "expected_http_status":200,
             "expected_body_contains":"zone-b-cloudflare-edge","min_independent_proofs":1,"expected_revision":"b"*40}
        d = self.kernel.evaluate_operational_transition(c,[r],now_utc=NOW)
        self.assertIn("ERR_RUNTIME_REVISION_MISMATCH:rcpt-1",d.error_codes)

if __name__ == "__main__":
    unittest.main()

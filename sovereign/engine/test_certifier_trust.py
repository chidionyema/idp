"""The certifier publishes its own public trust anchors, with no human step.

The worker pins whatever the settlement-trust ConfigMap holds, so this proves the values the
certifier writes are exactly the ones the REAL compiled gate and REAL yield verifier accept, and
that the worker identity can never equal, or sign as, the certifier. Only the cluster call is
injected: a unit test cannot reach the API server.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import stat
from pathlib import Path

import pytest

from sovereign.engine import certifier
from sovereign.engine.activities import (
    rust_gate_verify_settlement,
    verify_instruction_yield,
)

URL = "https://llm.meridianlabs.cloud/health"
ACCEPT = certifier.parse_accept(f'GET {URL} expect 200 contains "ok" within 30m')
TASK = "ship the thing"
EXPECTED = {
    "instruction_id": "INS-9",
    "run_id": "run-z",
    "epoch": 1,
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


class FakeCluster:
    def __init__(self, data=None, get_status=200, patch_status=200):
        self.data = dict(data or {})
        self.get_status, self.patch_status = get_status, patch_status
        self.calls: list[str] = []

    def __call__(self, method, url, body):
        self.calls.append(method)
        if method == "GET":
            return self.get_status, json.dumps({"data": self.data}).encode()
        if self.patch_status == 200:
            self.data.update(json.loads(body)["data"])
        return self.patch_status, b"{}"


def test_worker_identity_is_public_only_distinct_and_stable(tmp_path):
    key_dir = str(tmp_path / "keys")
    cert = certifier.public_key_hex(key_dir)
    worker = certifier.worker_identity_hex(key_dir)
    assert len(worker) == 64 and worker != cert
    assert certifier.worker_identity_hex(key_dir) == worker
    # No file in the key directory holds a private half for the worker.
    names = sorted(p.name for p in Path(key_dir).iterdir())
    assert names == [certifier.SEED_FILE, certifier.WORKER_IDENTITY_FILE]
    assert stat.S_IMODE(os.stat(Path(key_dir) / certifier.SEED_FILE).st_mode) == 0o600


def test_published_trust_makes_the_real_gate_and_verifier_allow(tmp_path, monkeypatch):
    key_dir = str(tmp_path / "keys")
    cluster = FakeCluster()
    assert (
        certifier.publish_trust(key_dir, namespace="temporal", kube=cluster)
        == "published"
    )
    for env, key in (
        ("ESTATE_YIELD_VERIFIER_PUBKEY_HEX", "yield_verifier_pubkey_hex"),
        ("ESTATE_SETTLEMENT_CERTIFIERS_HEX", "certifiers_hex"),
        ("ESTATE_WORKER_PUBKEY_HEX", "worker_pubkey_hex"),
        ("ESTATE_SETTLEMENT_POLICY_HASH", "policy_hash"),
    ):
        monkeypatch.setenv(env, cluster.data[key])
    monkeypatch.setenv("MERIDIAN_GATE_BIN", _gate())
    envelope = certifier.build_envelope(
        EXPECTED,
        ACCEPT,
        seed_env="UNSET_SEED_ENV",
        policy_hash=cluster.data["policy_hash"],
        getter=lambda _u: (200, b'{"status":"ok"}'),
        key_dir=key_dir,
    )
    payload = {"expected": EXPECTED, "envelope": envelope}
    assert asyncio.run(rust_gate_verify_settlement(payload)) == "allow"
    assert asyncio.run(verify_instruction_yield(payload)) == "settle"


def test_publish_is_idempotent_and_touches_nothing_when_unchanged(tmp_path):
    key_dir = str(tmp_path / "keys")
    cluster = FakeCluster()
    assert certifier.publish_trust(key_dir, namespace="t", kube=cluster) == "published"
    assert certifier.publish_trust(key_dir, namespace="t", kube=cluster) == "unchanged"
    assert cluster.calls == ["GET", "PATCH", "GET"]


def test_cluster_refusals_surface_as_refusals_not_silent_success(tmp_path):
    key_dir = str(tmp_path / "keys")
    with pytest.raises(certifier.CertifierRefusal):
        certifier.publish_trust(
            key_dir, namespace="t", kube=FakeCluster(get_status=403)
        )
    with pytest.raises(certifier.CertifierRefusal):
        certifier.publish_trust(
            key_dir, namespace="t", kube=FakeCluster(patch_status=403)
        )


def test_default_policy_is_pinned_and_stable():
    assert (
        certifier.DEFAULT_POLICY_HASH
        == hashlib.sha256(b"meridian-settlement-policy-v1").hexdigest()
    )


def test_a_worker_identity_equal_to_the_certifier_key_is_refused(tmp_path, monkeypatch):
    key_dir = str(tmp_path / "keys")
    cert = certifier.public_key_hex(key_dir)
    monkeypatch.setattr(certifier, "worker_identity_hex", lambda _d: cert)
    with pytest.raises(certifier.CertifierRefusal):
        certifier.trust_values(key_dir)
    monkeypatch.setattr(certifier, "worker_identity_hex", lambda _d: "not-a-key")
    with pytest.raises(certifier.CertifierRefusal):
        certifier.trust_values(key_dir)

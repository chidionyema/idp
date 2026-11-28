"""Autonomous certification: the certifier mints its own key and reads its own acceptance predicate.

No human generates a key or types an accept line. The signed envelopes are judged by the REAL
compiled `meridian-gate` and the REAL yield verifier, exactly as in test_certifier.py; only the
Temporal client, the GitHub comment read and the production GET are injected.
"""

# Pytest assertions are test checks, never runtime input validation.
# ruff: noqa: S101
from __future__ import annotations

import asyncio
import hashlib
import os
import stat
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sovereign.engine import certifier
from sovereign.engine.activities import (
    rust_gate_verify_settlement,
    verify_instruction_yield,
)

POLICY = "ef" * 32
AUTHORS = frozenset({"chidionyema"})
URL = "https://llm.meridianlabs.cloud/health"
CONTRACT = f'SHIP-CONTRACT\naccept: GET {URL} expect 200 contains "ok" within 30m\n'


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


def _comment(body, login="chidionyema", at="2026-11-28T01:00:00Z"):
    return {"body": body, "user": {"login": login}, "created_at": at}


class FakeHandle:
    def __init__(self, world, workflow_id):
        self.world, self.id = world, workflow_id

    async def query(self, _name):
        return self.world.states[self.id]

    async def describe(self):
        return SimpleNamespace(run_id=f"run-{self.id}")

    async def signal(self, name, envelope):
        self.world.signals.append((self.id, name, envelope))


class FakeClient:
    def __init__(self, states):
        self.states = states
        self.signals = []

    async def list_workflows(self, _query):
        for wid in self.states:
            yield SimpleNamespace(id=wid)

    def get_workflow_handle(self, workflow_id):
        return FakeHandle(self, workflow_id)


def _state(task, instruction_id="INS-9", status="running"):
    return {
        "instruction_id": instruction_id,
        "task": task,
        "step": 1,
        "status": status,
        "commit": None,
    }


def test_the_key_is_minted_once_private_and_never_in_the_published_half(tmp_path):
    key_dir = str(tmp_path / "keys")
    pub = certifier.public_key_hex(key_dir)
    seed_file = Path(key_dir) / certifier.SEED_FILE
    seed = seed_file.read_text()
    assert len(pub) == 64 and len(seed) == 64 and pub != seed
    assert stat.S_IMODE(seed_file.stat().st_mode) == 0o600
    assert certifier.public_key_hex(key_dir) == pub  # stable across restarts
    derived = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed))
    assert derived.public_key().public_bytes_raw().hex() == pub


def test_simultaneous_first_starts_end_with_one_key(tmp_path):
    key_dir = str(tmp_path / "keys")
    seen: list[str] = []
    gate = threading.Barrier(8)

    def worker():
        gate.wait()
        seen.append(certifier.mint_or_load_seed(key_dir))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len({s for s in seen if len(s) == 64}) == 1


def test_an_instruction_must_name_exactly_one_issue():
    assert (
        certifier.governing_issue("ship the fix for chidionyema/idp#8688 now") == 8688
    )
    assert certifier.governing_issue("see #8688 and #8688") == 8688
    for task in ("no issue here", "both #8688 and #8415", ""):
        with pytest.raises(certifier.CertifierRefusal):
            certifier.governing_issue(task)


def test_only_the_newest_contract_from_a_trusted_author_counts():
    old = _comment(CONTRACT.replace("health", "old"), at="2026-11-28T00:00:00Z")
    new = _comment(CONTRACT, at="2026-11-28T02:00:00Z")
    forged = _comment(
        CONTRACT.replace("health", "evil"), login="stranger", at="2026-11-28T03:00:00Z"
    )
    assert certifier.accept_from_comments([old, new, forged], AUTHORS).url == URL
    with pytest.raises(certifier.CertifierRefusal):
        certifier.accept_from_comments([forged], AUTHORS)
    with pytest.raises(certifier.CertifierRefusal):
        certifier.accept_from_comments([new], frozenset())
    with pytest.raises(certifier.CertifierRefusal):
        certifier.accept_from_comments([_comment("just a comment")], AUTHORS)


def _sweep(tmp_path, states, comments):
    client = FakeClient(states)
    outcomes = asyncio.run(
        certifier.sweep(
            client,
            key_dir=str(tmp_path / "keys"),
            policy_hash=POLICY,
            authors=AUTHORS,
            comments_for=lambda _issue: comments,
            getter=_ok,
        )
    )
    return client, outcomes


def test_a_swept_instruction_is_certified_and_both_real_verifiers_allow_it(
    tmp_path, monkeypatch
):
    pub = certifier.public_key_hex(str(tmp_path / "keys"))
    other = Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex()
    monkeypatch.setenv("MERIDIAN_GATE_BIN", _gate())
    monkeypatch.setenv("ESTATE_YIELD_VERIFIER_PUBKEY_HEX", pub)
    monkeypatch.setenv("ESTATE_SETTLEMENT_CERTIFIERS_HEX", pub)
    monkeypatch.setenv("ESTATE_WORKER_PUBKEY_HEX", other)
    monkeypatch.setenv("ESTATE_SETTLEMENT_POLICY_HASH", POLICY)
    task = "ship the thing for chidionyema/idp#8688"
    client, outcomes = _sweep(tmp_path, {"INS-9": _state(task)}, [_comment(CONTRACT)])
    assert outcomes == {"INS-9": "signalled"}
    ((wid, name, envelope),) = client.signals
    assert (wid, name) == ("INS-9", "submit_independent_yield")
    expected = {
        "instruction_id": "INS-9",
        "run_id": "run-INS-9",
        "epoch": 1,
        "goal_sha256": hashlib.sha256(task.encode()).hexdigest(),
        "commit_sha": None,
    }
    payload = {"expected": expected, "envelope": envelope}
    assert asyncio.run(rust_gate_verify_settlement(payload)) == "allow"
    assert asyncio.run(verify_instruction_yield(payload)) == "settle"


def test_nothing_is_signed_without_one_issue_a_trusted_contract_or_a_real_effect(
    tmp_path,
):
    states = {
        "INS-A": _state("no issue named", "INS-A"),
        "INS-B": _state("both #8688 and #8415", "INS-B"),
        "INS-C": _state("fix #8688", "INS-C"),
    }
    client, outcomes = _sweep(tmp_path, states, [_comment("no contract here")])
    assert client.signals == []
    assert set(outcomes) == {"INS-A", "INS-B", "INS-C"}
    assert all(v.startswith("refused:") for v in outcomes.values())

    proxy = _comment(CONTRACT.replace(URL, "https://raw.githubusercontent.com/a/b/c"))
    client, outcomes = _sweep(
        tmp_path, {"INS-C": _state("fix #8688", "INS-C")}, [proxy]
    )
    assert client.signals == []
    assert outcomes["INS-C"].startswith("refused:")

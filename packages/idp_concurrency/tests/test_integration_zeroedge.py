"""End-to-end integration: ZeroEdge ledger uses idp_concurrency MerkleLog.

This test is colocated in idp_concurrency because it crosses the package
boundary — it imports zeroedge's ledger and verifies the chain is real.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from zeroedge.ledger import CostLedger, LedgerRow  # noqa: E402


def test_zeroedge_ledger_writes_to_merkle_chain(tmp_path: Path):
    ledger = CostLedger(tmp_path / "cost.jsonl")
    chain_path = ledger.path.with_suffix(".chain.db")
    assert chain_path.exists(), "chain sibling should be opened on construction"

    for i in range(10):
        ledger.record(LedgerRow(request_id=f"r{i}", actual_cost_usd=0.001 * i))

    assert ledger.chain_length() == 10
    assert ledger.verify_chain() is True

    db = sqlite3.connect(chain_path)
    db.execute(
        "UPDATE chain SET payload = ? WHERE seq = 5",
        ['{"tampered": true}'],
    )
    db.commit()
    db.close()

    assert ledger.verify_chain() is False
    assert ledger.summary()["chain_ok"] is False


def test_zeroedge_ledger_chain_disabled_by_env(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("ZEROEDGE_CHAIN", "off")
    ledger = CostLedger(tmp_path / "cost.jsonl")
    ledger.record(LedgerRow(request_id="r0"))
    assert ledger.chain_length() == 0
    assert ledger.verify_chain() is True  # disabled chain is "ok"

"""Tests for merkle_log.MerkleLog."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from idp_concurrency.merkle_log import MerkleLog


def test_append_returns_monotonic_seq(tmp_path: Path):
    log = MerkleLog(tmp_path / "chain.db")
    s1 = log.append({"a": 1})
    s2 = log.append({"b": 2})
    s3 = log.append({"c": 3})
    assert s1 < s2 < s3


def test_chain_verifies_on_clean_log(tmp_path: Path):
    log = MerkleLog(tmp_path / "chain.db")
    log.append({"request_id": "r1", "cost": 0.01})
    log.append({"request_id": "r2", "cost": 0.02})
    log.append({"request_id": "r3", "cost": 0.03})
    assert log.verify() is True


def test_tampering_with_payload_breaks_chain(tmp_path: Path):
    log = MerkleLog(tmp_path / "chain.db")
    log.append({"request_id": "r1", "cost": 0.01})
    log.append({"request_id": "r2", "cost": 0.02})
    log.append({"request_id": "r3", "cost": 0.03})

    # Tamper with row 2's payload in place.
    db = sqlite3.connect(log.path)
    db.execute(
        "UPDATE chain SET payload = ? WHERE seq = 2",
        ['{"request_id": "r2", "cost": 0.99}'],
    )
    db.commit()
    db.close()

    assert log.verify() is False


def test_deleting_a_row_breaks_chain(tmp_path: Path):
    log = MerkleLog(tmp_path / "chain.db")
    log.append({"a": 1})
    log.append({"a": 2})
    log.append({"a": 3})

    db = sqlite3.connect(log.path)
    db.execute("DELETE FROM chain WHERE seq = 2")
    db.commit()
    db.close()

    assert log.verify() is False


def test_uses_wal_journal_mode(tmp_path: Path):
    log = MerkleLog(tmp_path / "chain.db")
    mode = log.db.execute("PRAGMA journal_mode").fetchone()[0].lower()
    assert mode == "wal"


def test_reopen_continues_chain(tmp_path: Path):
    p = tmp_path / "chain.db"
    log1 = MerkleLog(p)
    last_seq_before = log1.append({"x": 1})
    log1.append({"x": 2})

    log2 = MerkleLog(p)
    last_seq_after = log2.append({"x": 3})

    assert last_seq_after > last_seq_before
    assert log2.verify() is True


def test_empty_log_verifies(tmp_path: Path):
    log = MerkleLog(tmp_path / "chain.db")
    assert log.verify() is True

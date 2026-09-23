"""Phase D — SQLite WAL + SHA-256 Merkle chain.

`Receipt = f(Trace)`: every row's hash includes the previous row's hash.
`verify()` walks the chain end-to-end; any tampering is detected.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class MerkleLog:
    """Append-only, tamper-evident log backed by SQLite WAL."""

    ZERO = "0" * 64

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS chain(
                   seq        INTEGER PRIMARY KEY AUTOINCREMENT,
                   prev_hash  TEXT    NOT NULL,
                   row_hash   TEXT    NOT NULL,
                   payload    TEXT    NOT NULL,
                   ts         REAL    NOT NULL
               )"""
        )

    def _tail(self) -> str:
        row = self.db.execute("SELECT row_hash FROM chain ORDER BY seq DESC LIMIT 1").fetchone()
        return row[0] if row else self.ZERO

    def append(self, payload: dict[str, Any]) -> int:
        prev = self._tail()
        canon = json.dumps(payload, sort_keys=True, default=str)
        h = hashlib.sha256(f"{prev}|{canon}".encode()).hexdigest()
        cur = self.db.execute(
            "INSERT INTO chain(prev_hash,row_hash,payload,ts) VALUES (?,?,?,?)",
            (prev, h, canon, time.time()),
        )
        return cur.lastrowid

    def verify(self) -> bool:
        prev = self.ZERO
        for _seq, prev_h, row_h, payload, _ts in self.db.execute(
            "SELECT seq,prev_hash,row_hash,payload,ts FROM chain ORDER BY seq"
        ):
            if prev_h != prev:
                return False
            if hashlib.sha256(f"{prev}|{payload}".encode()).hexdigest() != row_h:
                return False
            prev = row_h
        return True

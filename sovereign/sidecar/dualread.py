"""Dual-read router (cp10): every read runs twice -- once against the
legacy DB, once by walking cp8/cp9's DAG from `.estate/heads/shadow_main`
-- and the two are compared, hashed, and recorded, without ever slowing
the caller past the configured budget.

read() never blocks or delays the legacy read on the DAG side: the legacy
query runs first and its result is what read() returns, so a slow or
broken DAG walk degrades the receipt, never the answer the caller gets.
This mirrors cp8's "never blocks the legacy write" contract one hop over,
on the read path.

Row identity is the sqlite rowid, the same identity cp8's DAG nodes
already carry (sovereign/sidecar/core.py) -- the DAG walk here looks for
the first node for (table, rowid) walking backward from the shadow root,
which is exactly the DAG's current-state view of that row.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import shadow_root

# Mirrors sovereign.sidecar.core._IDENT_RE exactly -- table names here are
# always a sidecar's own configured target, never free-form user input,
# but the check stays cheap insurance against a bad config value reaching
# raw SQL string interpolation (LAW 46: no literal path/host/table sits
# unchecked in an f-string).
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _dag_row(dag_dir: Path, table: str, rowid: int) -> dict[str, Any] | None:
    """Walks the DAG backward from the current shadow root looking for
    the first node touching (table, rowid). Returns None if the row was
    last deleted, if it was never observed, or if there is no shadow
    root yet (nothing drained) -- never raises on a missing head or a
    missing node file, since a stale/absent DAG view is exactly what
    read() must detect and report, not crash on."""
    head_path = shadow_root.head_path()
    if not head_path.exists():
        return None
    try:
        head = json.loads(head_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None

    node_hash = head.get("root")
    seen: set[str] = set()
    while node_hash and node_hash != shadow_root.GENESIS_NODE_HASH:
        if node_hash in seen:
            return None  # a cycle is the same "fail closed" cp9 already applies
        seen.add(node_hash)
        node_path = dag_dir / f"{node_hash}.json"
        if not node_path.exists():
            return None
        try:
            body = json.loads(node_path.read_text())
        except (OSError, json.JSONDecodeError):
            return None
        if body.get("table") == table and body.get("rowid") == rowid:
            return None if body.get("op") == "DELETE" else body.get("row")
        node_hash = body.get("prev_node_hash", shadow_root.GENESIS_NODE_HASH)
    return None


def _hash_row(row: dict[str, Any] | None) -> str:
    return hashlib.sha256(config.canonical_json({"row": row})).hexdigest()


def read(conn: sqlite3.Connection, table: str, rowid: int, dag_dir: Path | None = None) -> dict[str, Any]:
    """Returns {"row", "match", "legacy_ms", "dag_ms", "overhead_ms"}.
    `row` is always the legacy DB's answer -- the DAG side only ever
    informs `match` and the receipt, never what the caller sees."""
    if not _IDENT_RE.match(table):
        raise ValueError(f"not a safe table identifier: {table!r}")
    dag_dir = dag_dir or config.SIDECAR_DAG_DIR

    start = time.perf_counter()

    t0 = time.perf_counter()
    cur = conn.execute(f"SELECT * FROM {table} WHERE rowid = ?", (rowid,))
    cols = [d[0] for d in cur.description]
    fetched = cur.fetchone()
    legacy_row = dict(zip(cols, fetched)) if fetched is not None else None
    legacy_ms = (time.perf_counter() - t0) * config.MS_PER_SECOND

    t1 = time.perf_counter()
    dag_row = _dag_row(dag_dir, table, rowid)
    dag_ms = (time.perf_counter() - t1) * config.MS_PER_SECOND

    legacy_hash = _hash_row(legacy_row)
    dag_hash = _hash_row(dag_row)
    match = legacy_hash == dag_hash

    receipts_mod.append(
        {
            "kind": "dualread",
            "table": table,
            "rowid": rowid,
            "legacy_hash": legacy_hash,
            "dag_hash": dag_hash,
            "legacy_ms": round(legacy_ms, config.DUALREAD_LATENCY_ROUND_NDIGITS),
            "dag_ms": round(dag_ms, config.DUALREAD_LATENCY_ROUND_NDIGITS),
            "match": match,
        }
    )

    overhead_ms = (time.perf_counter() - start) * config.MS_PER_SECOND - legacy_ms
    return {
        "row": legacy_row,
        "match": match,
        "legacy_ms": legacy_ms,
        "dag_ms": dag_ms,
        "overhead_ms": overhead_ms,
    }

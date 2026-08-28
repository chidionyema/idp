"""sovereign/sidecar (cp8): every legacy write is diffed, hashed, and
passed through untouched.

Founder, 2026-08-25: "If legacy DB consistency is hard, build the
sidecar." This estate's sqlite3 build (Anaconda-packaged, the same one
sovereign-bus ships and runs under) has no
sqlite3.Connection.set_update_hook -- confirmed absent on both the
sovereign/.venv interpreter and the system one -- so a Python-level hook
on an already-open connection cannot be used. Two narrower workarounds
were tried and both fail for the same reason (sqlite3.Connection is a
C-extension type): shadowing an instance method (`conn.execute = ...`
raises "attribute is read-only") and reassigning `__class__` to a Python
subclass (raises "assignment only supported for mutable types").

attach() instead adds one shadow log table (`_sb_sidecar_log`, shared
across every attached table) and three AFTER triggers -- INSERT, UPDATE,
DELETE -- on the target table. A SQL trigger is a core SQLite feature
available under any build, any Python, any client language; it fires
inside the same transaction as the write it observes and cannot veto,
delay or rewrite it, so the sidecar can only ever observe, by
construction. This is also the correct shape for the real target: sitting
on maestro's write path without editing maestro.py, since maestro opens
its own connections and a trigger is attached to the *database*, not to
any one connection.

drain() is the only place I/O to the DAG directory happens. It reads the
queued log rows, turns each into a Merkle DAG node (a JSON file at
<sidecar.dag_dir>/<sha256 hex of the node body>.json, chained via
prev_node_hash the same way sovereign.engine.receipts chains its lines)
plus one receipts entry of kind "sidecar_write", then deletes the log row
-- only after both writes succeed. If the DAG directory is not writable
(disk full, permissions, a mount gone away), the exception is caught here
and the log row is left queued, never lost and never blocking the legacy
write that already committed. The next drain() that succeeds first
appends one receipt of kind "sidecar_degraded" recording how many writes
were queued while the DAG was unwritable, so the gap is itself an
auditable event rather than a silent hole in the chain.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any

from sovereign import config
from sovereign.engine import dag as dag_mod
from sovereign.engine import receipts as receipts_mod
from sovereign.engine import shadow_root

GENESIS_NODE_HASH = "0" * config.RECEIPTS_HASH_HEX_LEN

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_LOG_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS _sb_sidecar_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    tbl TEXT NOT NULL,
    op TEXT NOT NULL,
    rid INTEGER NOT NULL
)
"""


def _trigger_ddl(table: str) -> list[str]:
    return [
        f"""CREATE TRIGGER IF NOT EXISTS _sb_sidecar_ins_{table}
            AFTER INSERT ON {table} BEGIN
                INSERT INTO _sb_sidecar_log (tbl, op, rid) VALUES ('{table}', 'INSERT', NEW.rowid);
            END""",
        f"""CREATE TRIGGER IF NOT EXISTS _sb_sidecar_upd_{table}
            AFTER UPDATE ON {table} BEGIN
                INSERT INTO _sb_sidecar_log (tbl, op, rid) VALUES ('{table}', 'UPDATE', NEW.rowid);
            END""",
        f"""CREATE TRIGGER IF NOT EXISTS _sb_sidecar_del_{table}
            AFTER DELETE ON {table} BEGIN
                INSERT INTO _sb_sidecar_log (tbl, op, rid) VALUES ('{table}', 'DELETE', OLD.rowid);
            END""",
    ]


def _trigger_names(table: str) -> list[str]:
    return [f"_sb_sidecar_ins_{table}", f"_sb_sidecar_upd_{table}", f"_sb_sidecar_del_{table}"]


class DBSidecar:
    """One instance per (connection, table). Thread-unsafe by the same
    contract a sqlite3.Connection already is: one sidecar per connection,
    used only from the thread that owns that connection.

    UPDATE/DELETE are logged with their rowid but, for DELETE, the row is
    already gone by drain() time -- there is no update_hook and no
    RETURNING-clause rewrite of the legacy SQL (that would be exactly the
    "DB logic changed" this sidecar must never do). A DELETE node
    therefore carries row=None. Capturing pre-delete content is a
    documented residual for a later checkpoint; every scenario in
    features/sovereign-bus/cp8_db_sidecar.feature is INSERT-shaped and is
    covered exactly."""

    def __init__(self, conn: sqlite3.Connection, table: str, dag_dir: Path | None = None) -> None:
        if not _IDENT_RE.match(table):
            raise ValueError(f"not a safe table identifier: {table!r}")
        self._conn = conn
        self._table = table
        self._dag_dir = dag_dir or config.SIDECAR_DAG_DIR
        self._lock = threading.Lock()
        self.missed = 0

    def attach(self) -> "DBSidecar":
        self._conn.execute(_LOG_TABLE_DDL)
        for ddl in _trigger_ddl(self._table):
            self._conn.execute(ddl)
        self._conn.commit()
        return self

    def detach(self) -> None:
        for name in _trigger_names(self._table):
            self._conn.execute(f"DROP TRIGGER IF EXISTS {name}")
        self._conn.commit()

    def drain(self) -> int:
        """Turns every queued log row for this table into a DAG node plus
        a sidecar_write receipt, in order, deleting each log row only
        after both writes land. Returns how many were processed. Never
        raises: a DAG-directory failure leaves the remainder queued and
        is recorded, not propagated -- this is the only place cp8's "never
        blocks the legacy write" guarantee has to hold, since drain() runs
        after the legacy write already committed."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT seq, op, rid FROM _sb_sidecar_log WHERE tbl = ? ORDER BY seq", (self._table,)
            ).fetchall()
            if not rows:
                return 0
            processed = 0
            try:
                for seq, op, rid in rows:
                    self._write_node(op, rid)
                    self._conn.execute("DELETE FROM _sb_sidecar_log WHERE seq = ?", (seq,))
                    self._conn.commit()
                    processed += 1
            except OSError:
                self.missed = len(rows) - processed
                return processed
            if self.missed:
                receipts_mod.append({"kind": "sidecar_degraded", "table": self._table, "missed": self.missed})
                self.missed = 0
            return processed

    def recover_if_writable(self) -> bool:
        """Alias kept for callers that only want to know "did draining
        flush a degraded receipt", e.g. a health-check loop that does not
        care about the processed count."""
        had_missed = self.missed > 0
        self.drain()
        return had_missed and self.missed == 0

    def _row(self, rowid: int) -> dict[str, Any] | None:
        cur = self._conn.execute(f"SELECT * FROM {self._table} WHERE rowid = ?", (rowid,))
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    def _last_node_hash(self) -> str:
        marker = self._dag_dir / config.SIDECAR_HEAD_FILENAME
        if not marker.exists():
            return GENESIS_NODE_HASH
        try:
            return json.loads(marker.read_text())["hash"]
        except (OSError, json.JSONDecodeError, KeyError):
            return GENESIS_NODE_HASH

    def _write_node(self, op: str, rowid: int) -> None:
        row = self._row(rowid) if op != "DELETE" else None
        body = {
            "op": op,
            "table": self._table,
            "rowid": rowid,
            "row": row,
            "prev_node_hash": self._last_node_hash(),
        }
        node_hash = hashlib.sha256(config.canonical_json(body)).hexdigest()
        self._dag_dir.mkdir(parents=True, exist_ok=True)
        (self._dag_dir / f"{node_hash}.json").write_text(json.dumps(body, sort_keys=True))
        (self._dag_dir / config.SIDECAR_HEAD_FILENAME).write_text(json.dumps({"hash": node_hash}, sort_keys=True))
        receipts_mod.append(
            {"kind": "sidecar_write", "table": self._table, "node_hash": node_hash, "op": op, "rowid": rowid}
        )
        # cp9: the shadow root advances exactly once per drained write --
        # after the node + receipt it names both already exist, never
        # before. shadow_main is a convenience pointer to a node that is
        # already durable (the DAG file + receipt above); if writing it
        # fails, that must not re-queue the row (the write already
        # happened, above) or drain() would double-write the node on
        # retry, so it is swallowed here rather than propagated into
        # drain()'s except OSError.
        try:
            shadow_root.update_head(node_hash, self._dag_dir)
        except dag_mod.HeadOutsideDagRootError as exc:
            # R15: this sidecar's DAG directory is not under the
            # configured DAG root, so advancing the estate's shared head
            # to it would leave a pointer that dangles the moment this
            # directory goes away. Refusing is correct; refusing SILENTLY
            # is how the original defect survived, so the refusal is a
            # line in the signed chain.
            receipts_mod.append(
                {"kind": "head_refused", "table": self._table, "node_hash": node_hash, "text": str(exc)}
            )
        except OSError:
            pass


def attach(conn: sqlite3.Connection, table: str, dag_dir: Path | None = None) -> DBSidecar:
    """The one entry point: `attach(conn, "episodes")` on an already-open
    legacy connection. Adds a shadow log table and three triggers to the
    database itself (not the connection), so it observes writes from any
    connection to that database, not just this one. Returns the DBSidecar
    so a caller can `.drain()`, `.detach()` or `.recover_if_writable()` it
    later; never wraps or replaces the connection the legacy code already
    uses, and never touches the target table's own schema."""
    return DBSidecar(conn, table, dag_dir).attach()

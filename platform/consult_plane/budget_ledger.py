"""Micro-USD budget governance for the consultation plane.

This module is NOT the estate's memory plane and NOT a second spend ledger of
record. It is the enforcement surface for one consultation: how much of a
bounded budget may be committed, how much is in flight, how much is disputed,
and what is left. The estate's founder-visible spend ledger already exists in
penny-core (`platform/llm/pennyd/crates/penny-core/src/ledger.rs`, integer
nano-USD) and its per-key daily budgets live in `budget.rs`. Neither carries a
four-bucket conservation identity with an escrow/dispute state, and neither is
scoped per instruction. This module is the per-instruction conservation
envelope in front of those ledgers, not a replacement for them.

It also carries the Tier-0 consult digest cache: an identical consultation
(intent + invariant version + evidence hashes) is served from a local cache at
zero cost, with no model call and no upstream fetch.

Standard library only. No local browser is ever launched: the transport names
that would imply one are refused mechanically, so a consultation can never
reach for a local Chrome to answer a question.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

# Transports that would drive a local browser or scrape a web chat UI. The
# estate runs browsers on Lane 1 edge, never on the founder's laptop; a
# consultation that reaches for a local Chrome is a consultation that spends
# unbounded time and unbounded memory on the thin client. Refused by name.
FORBIDDEN_TRANSPORTS = frozenset(
    {
        "chrome",
        "chromium",
        "local_browser",
        "puppeteer_local",
        "playwright_local",
        "web_chat_scrape",
    }
)


class BudgetError(RuntimeError):
    """Base failure for micro-USD budget governance."""


class BrowserTransportForbiddenError(BudgetError):
    """Raised when an agent attempts local browser/Chrome consultation."""


class BudgetExceededError(BudgetError):
    """Raised fail-closed when monthly, daily, or per-instruction caps are exceeded."""


class ConservationViolationError(BudgetError):
    """Raised if the 4-bucket conservation identity drifts by even 1 uUSD."""


@dataclass(frozen=True)
class BudgetSnapshot:
    """The four buckets. Their sum is the monthly cap, always."""

    monthly_cap_uusd: int
    available_uusd: int
    inflight_reserved_uusd: int
    escrow_disputed_uusd: int
    settled_uusd: int

    @property
    def total_uusd(self) -> int:
        return (
            self.available_uusd
            + self.inflight_reserved_uusd
            + self.escrow_disputed_uusd
            + self.settled_uusd
        )


class MicroUsdLedger:
    """SQLite WAL 4-bucket micro-USD ledger (1 USD = 1_000_000 uUSD).

    The conservation identity is checked inside every mutating transaction, so
    a drift cannot be committed by a partially applied write: the transaction
    rolls back and the violation is raised.
    """

    def __init__(
        self,
        db_path: str = ":memory:",
        monthly_cap_uusd: int = 200_000_000,
        default_daily_cap_uusd: int = 10_000_000,
        default_instruction_cap_uusd: int = 500_000,
    ) -> None:
        if monthly_cap_uusd <= 0:
            raise ValueError("monthly_cap_uusd must be positive")
        self.default_daily_cap_uusd = default_daily_cap_uusd
        self.default_instruction_cap_uusd = default_instruction_cap_uusd
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema(monthly_cap_uusd)

    def _init_schema(self, monthly_cap_uusd: int) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS budget_buckets (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                monthly_cap_uusd INTEGER NOT NULL,
                available_uusd INTEGER NOT NULL CHECK (available_uusd >= 0),
                inflight_reserved_uusd INTEGER NOT NULL CHECK (inflight_reserved_uusd >= 0),
                escrow_disputed_uusd INTEGER NOT NULL CHECK (escrow_disputed_uusd >= 0),
                settled_uusd INTEGER NOT NULL CHECK (settled_uusd >= 0)
            );
            CREATE TABLE IF NOT EXISTS budget_leases (
                lease_id TEXT PRIMARY KEY,
                instruction_id TEXT NOT NULL,
                day_utc TEXT NOT NULL,
                role TEXT NOT NULL,
                transport TEXT NOT NULL,
                reserved_uusd INTEGER NOT NULL CHECK (reserved_uusd >= 0),
                settled_uusd INTEGER NOT NULL DEFAULT 0 CHECK (settled_uusd >= 0),
                status TEXT NOT NULL CHECK (status IN ('INFLIGHT', 'SETTLED', 'RELEASED', 'DISPUTED')),
                created_at_epoch INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS consult_cache (
                digest TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                created_at_epoch INTEGER NOT NULL,
                ttl_seconds INTEGER NOT NULL CHECK (ttl_seconds > 0)
            );
            """
        )
        cur = self._conn.execute("SELECT COUNT(*) FROM budget_buckets WHERE id = 1")
        if cur.fetchone()[0] == 0:
            self._conn.execute(
                """
                INSERT INTO budget_buckets (
                    id, monthly_cap_uusd, available_uusd,
                    inflight_reserved_uusd, escrow_disputed_uusd, settled_uusd
                ) VALUES (1, ?, ?, 0, 0, 0)
                """,
                (monthly_cap_uusd, monthly_cap_uusd),
            )
        self.assert_conservation()

    def snapshot(self) -> BudgetSnapshot:
        row = self._conn.execute(
            """
            SELECT monthly_cap_uusd, available_uusd, inflight_reserved_uusd,
                   escrow_disputed_uusd, settled_uusd
            FROM budget_buckets WHERE id = 1
            """
        ).fetchone()
        return BudgetSnapshot(*row)

    def assert_conservation(self) -> BudgetSnapshot:
        snap = self.snapshot()
        if snap.total_uusd != snap.monthly_cap_uusd:
            raise ConservationViolationError(
                f"4-bucket drift: {snap.total_uusd} != {snap.monthly_cap_uusd}"
            )
        return snap

    @staticmethod
    def _utc_day(now_epoch: Optional[int] = None) -> str:
        ts = now_epoch if now_epoch is not None else int(time.time())
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")

    def reserve(
        self,
        instruction_id: str,
        role: str,
        estimated_uusd: int,
        transport: str = "stateless_api",
        max_instruction_uusd: Optional[int] = None,
        max_daily_uusd: Optional[int] = None,
        now_epoch: Optional[int] = None,
    ) -> str:
        norm_transport = transport.strip().lower()
        if norm_transport in FORBIDDEN_TRANSPORTS:
            raise BrowserTransportForbiddenError(
                f"DENY: forbidden transport '{transport}'; "
                "use stateless_api or lane1_browser_rendering"
            )
        if estimated_uusd < 0:
            raise ValueError("estimated_uusd must be non-negative")

        ts = now_epoch if now_epoch is not None else int(time.time())
        day = self._utc_day(ts)
        inst_cap = max_instruction_uusd or self.default_instruction_cap_uusd
        day_cap = max_daily_uusd or self.default_daily_cap_uusd
        lease_id = f"lease_{uuid.uuid4().hex[:16]}"

        self._conn.execute("BEGIN IMMEDIATE")
        try:
            snap = self.assert_conservation()
            if estimated_uusd > snap.available_uusd:
                raise BudgetExceededError(
                    f"Monthly budget exhausted: need {estimated_uusd} uUSD, "
                    f"available {snap.available_uusd} uUSD"
                )

            inst_committed = self._conn.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN status = 'INFLIGHT' THEN reserved_uusd
                                         WHEN status IN ('SETTLED', 'DISPUTED') THEN settled_uusd
                                         ELSE 0 END), 0)
                FROM budget_leases WHERE instruction_id = ?
                """,
                (instruction_id,),
            ).fetchone()[0]
            if inst_committed + estimated_uusd > inst_cap:
                raise BudgetExceededError(
                    f"Instruction cap exceeded for {instruction_id}: "
                    f"{inst_committed + estimated_uusd} > {inst_cap}"
                )

            day_committed = self._conn.execute(
                """
                SELECT COALESCE(SUM(CASE WHEN status = 'INFLIGHT' THEN reserved_uusd
                                         WHEN status IN ('SETTLED', 'DISPUTED') THEN settled_uusd
                                         ELSE 0 END), 0)
                FROM budget_leases WHERE day_utc = ?
                """,
                (day,),
            ).fetchone()[0]
            if day_committed + estimated_uusd > day_cap:
                raise BudgetExceededError(
                    f"Daily cap exceeded for {day}: {day_committed + estimated_uusd} > {day_cap}"
                )

            self._conn.execute(
                """
                UPDATE budget_buckets
                SET available_uusd = available_uusd - ?,
                    inflight_reserved_uusd = inflight_reserved_uusd + ?
                WHERE id = 1
                """,
                (estimated_uusd, estimated_uusd),
            )
            self._conn.execute(
                """
                INSERT INTO budget_leases (
                    lease_id, instruction_id, day_utc, role, transport,
                    reserved_uusd, settled_uusd, status, created_at_epoch
                ) VALUES (?, ?, ?, ?, ?, ?, 0, 'INFLIGHT', ?)
                """,
                (
                    lease_id,
                    instruction_id,
                    day,
                    role,
                    norm_transport,
                    estimated_uusd,
                    ts,
                ),
            )
            self.assert_conservation()
            self._conn.execute("COMMIT")
            return lease_id
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def settle(self, lease_id: str, actual_uusd: int) -> BudgetSnapshot:
        if actual_uusd < 0:
            raise ValueError("actual_uusd must be non-negative")
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                "SELECT reserved_uusd, status FROM budget_leases WHERE lease_id = ?",
                (lease_id,),
            ).fetchone()
            if not row or row[1] != "INFLIGHT":
                raise BudgetError(f"Lease {lease_id} is not INFLIGHT")
            reserved_uusd = row[0]
            snap = self.assert_conservation()

            if actual_uusd <= reserved_uusd:
                refund = reserved_uusd - actual_uusd
                self._conn.execute(
                    """
                    UPDATE budget_buckets
                    SET available_uusd = available_uusd + ?,
                        inflight_reserved_uusd = inflight_reserved_uusd - ?,
                        settled_uusd = settled_uusd + ?
                    WHERE id = 1
                    """,
                    (refund, reserved_uusd, actual_uusd),
                )
            else:
                overrun = actual_uusd - reserved_uusd
                if overrun > snap.available_uusd:
                    raise BudgetExceededError(
                        f"Actual spend overrun ({overrun} uUSD) exceeds "
                        f"available {snap.available_uusd} uUSD"
                    )
                self._conn.execute(
                    """
                    UPDATE budget_buckets
                    SET available_uusd = available_uusd - ?,
                        inflight_reserved_uusd = inflight_reserved_uusd - ?,
                        settled_uusd = settled_uusd + ?
                    WHERE id = 1
                    """,
                    (overrun, reserved_uusd, actual_uusd),
                )

            self._conn.execute(
                "UPDATE budget_leases SET settled_uusd = ?, status = 'SETTLED' WHERE lease_id = ?",
                (actual_uusd, lease_id),
            )
            snap = self.assert_conservation()
            self._conn.execute("COMMIT")
            return snap
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def release(self, lease_id: str) -> BudgetSnapshot:
        """Release an unused reservation: the whole amount returns to available."""
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                "SELECT reserved_uusd, status FROM budget_leases WHERE lease_id = ?",
                (lease_id,),
            ).fetchone()
            if not row or row[1] != "INFLIGHT":
                raise BudgetError(f"Lease {lease_id} is not INFLIGHT")
            reserved_uusd = row[0]
            self._conn.execute(
                """
                UPDATE budget_buckets
                SET available_uusd = available_uusd + ?,
                    inflight_reserved_uusd = inflight_reserved_uusd - ?
                WHERE id = 1
                """,
                (reserved_uusd, reserved_uusd),
            )
            self._conn.execute(
                "UPDATE budget_leases SET status = 'RELEASED' WHERE lease_id = ?",
                (lease_id,),
            )
            snap = self.assert_conservation()
            self._conn.execute("COMMIT")
            return snap
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def dispute(self, lease_id: str) -> BudgetSnapshot:
        """Move a reservation into escrow: the money is still committed, not spent."""
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                "SELECT reserved_uusd, status FROM budget_leases WHERE lease_id = ?",
                (lease_id,),
            ).fetchone()
            if not row or row[1] != "INFLIGHT":
                raise BudgetError(f"Lease {lease_id} is not INFLIGHT")
            reserved_uusd = row[0]
            self._conn.execute(
                """
                UPDATE budget_buckets
                SET inflight_reserved_uusd = inflight_reserved_uusd - ?,
                    escrow_disputed_uusd = escrow_disputed_uusd + ?
                WHERE id = 1
                """,
                (reserved_uusd, reserved_uusd),
            )
            self._conn.execute(
                "UPDATE budget_leases SET settled_uusd = ?, status = 'DISPUTED' WHERE lease_id = ?",
                (reserved_uusd, lease_id),
            )
            snap = self.assert_conservation()
            self._conn.execute("COMMIT")
            return snap
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    @staticmethod
    def compute_consult_digest(
        invariant_version: str,
        intent_text: str,
        evidence_hashes: list,
    ) -> str:
        """The Tier-0 cache key: invariant version + normalized intent + evidence."""
        canonical = json.dumps(
            {
                "invariant_version": invariant_version,
                "intent": " ".join(intent_text.strip().split()),
                "evidence_hashes": sorted(evidence_hashes),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get_cached_consult(
        self, digest: str, now_epoch: Optional[int] = None
    ) -> Optional[dict]:
        ts = now_epoch if now_epoch is not None else int(time.time())
        row = self._conn.execute(
            "SELECT payload_json, created_at_epoch, ttl_seconds FROM consult_cache WHERE digest = ?",
            (digest,),
        ).fetchone()
        if not row:
            return None
        payload_json, created_at, ttl = row
        if ts >= created_at + ttl:
            return None
        return json.loads(payload_json)

    def put_cached_consult(
        self,
        digest: str,
        payload: dict,
        ttl_seconds: int = 86400,
        now_epoch: Optional[int] = None,
    ) -> None:
        ts = now_epoch if now_epoch is not None else int(time.time())
        self._conn.execute(
            """
            INSERT INTO consult_cache (digest, payload_json, created_at_epoch, ttl_seconds)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(digest) DO UPDATE SET
                payload_json = excluded.payload_json,
                created_at_epoch = excluded.created_at_epoch,
                ttl_seconds = excluded.ttl_seconds
            """,
            (digest, json.dumps(payload, sort_keys=True), ts, ttl_seconds),
        )

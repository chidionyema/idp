"""Decision-Mode Founder Protection Firewall.

FOUNDER_INTERVENTION_AS_DEFECT: every founder decision that is not a guarded
path seal is a defect in the automation that should have made it unnecessary.
The firewall makes that mechanical -- it logs a defect item on every admitted
non-guarded-path escalation, so the missing law or verifier gets engineered out
instead of being asked again next week.

An escalation may cross only when BOTH hold:

  * Proof-of-Exhaustion: a verified PoE receipt AND a verified consult digest
    exist for this instruction. An agent that has not exhausted deterministic
    discovery and dialectical consultation cannot reach the founder.
  * Admission class: one of exactly four. A debugging question or an
    unverified status request is not an escalation.

Admitted escalations are compiled into a fixed 5-field card with bounded
options and one-tap tokens, not a wall of prose. Non-outage cards coalesce
into one digest so the founder is interrupted once, not once per agent.

This module does NOT deliver anything. Delivery stays with the estate's
existing doors (`bin/estate-notify-done`, `bin/estate-fleet-telegram`); this
decides WHAT may be delivered and packages it.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Optional


class AdmissionClass(str, Enum):
    GUARDED_PATH_SEAL = "GUARDED_PATH_SEAL"
    IRREVERSIBLE_POLICY_TRADEOFF = "IRREVERSIBLE_POLICY_TRADEOFF"
    EXTERNAL_BOUNDARY_CREDENTIAL = "EXTERNAL_BOUNDARY_CREDENTIAL"
    CRITICAL_SERVICE_OUTAGE = "CRITICAL_SERVICE_OUTAGE"


class FounderFirewallDenyError(RuntimeError):
    """Raised when an unexhausted, out-of-scope, or malformed escalation tries to ping."""


@dataclass(frozen=True)
class DecisionOption:
    option_id: str  # e.g. "A", "B", "C"
    label: str
    blast_radius: str


@dataclass(frozen=True)
class DecisionMemoCard:
    """The fixed 5-field contract. No prose walls: every field is bounded."""

    instruction_id: str
    base_sha: str
    admission_class: AdmissionClass
    deadlock_summary: str  # Exactly one line, <= 160 chars.
    autonomy_stop_reason: (
        str  # The exact falsifier, guarded path, or outage probe failure.
    )
    options: tuple  # Strictly 2 or 3 bounded options.
    recommended_option_id: str
    poe_receipt_id: Optional[str] = None
    consult_digest: Optional[str] = None
    outage_probe_receipt: Optional[str] = None


@dataclass(frozen=True)
class AdmittedDecision:
    card_id: str
    delivery_mode: str  # "IMMEDIATE_ALERT" | "COALESCED_DIGEST"
    one_tap_tokens: dict
    defect_logged: bool


class DecisionModeFirewall:
    """The mechanical boundary protecting the founder's attention."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS exhaustion_receipts (
                instruction_id TEXT NOT NULL,
                poe_receipt_id TEXT NOT NULL,
                consult_digest TEXT NOT NULL,
                recorded_at_epoch INTEGER NOT NULL,
                PRIMARY KEY (instruction_id, poe_receipt_id, consult_digest)
            );
            CREATE TABLE IF NOT EXISTS founder_decision_queue (
                card_id TEXT PRIMARY KEY,
                instruction_id TEXT NOT NULL,
                admission_class TEXT NOT NULL,
                delivery_mode TEXT NOT NULL,
                card_json TEXT NOT NULL,
                one_tap_tokens_json TEXT NOT NULL,
                dispatched INTEGER NOT NULL DEFAULT 0,
                created_at_epoch INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS founder_defect_ratchet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT NOT NULL,
                instruction_id TEXT NOT NULL,
                admission_class TEXT NOT NULL,
                missing_automation_reason TEXT NOT NULL,
                recorded_at_epoch INTEGER NOT NULL
            );
            """
        )

    def register_exhaustion(
        self,
        instruction_id: str,
        poe_receipt_id: str,
        consult_digest: str,
        now_epoch: Optional[int] = None,
    ) -> None:
        """Record that discovery AND consultation ran for this instruction."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        self._conn.execute(
            """
            INSERT OR REPLACE INTO exhaustion_receipts (
                instruction_id, poe_receipt_id, consult_digest, recorded_at_epoch
            ) VALUES (?, ?, ?, ?)
            """,
            (instruction_id, poe_receipt_id, consult_digest, ts),
        )

    def submit(
        self,
        card: DecisionMemoCard,
        raw_class_override: Optional[str] = None,
        now_epoch: Optional[int] = None,
    ) -> AdmittedDecision:
        """Admit or refuse one escalation. Refusal is the default."""
        ts = now_epoch if now_epoch is not None else int(time.time())

        # 1. The strict four-class whitelist.
        if raw_class_override is not None:
            try:
                AdmissionClass(raw_class_override)
            except ValueError as exc:
                raise FounderFirewallDenyError(
                    f"FOUNDER_FIREWALL_DENY: '{raw_class_override}' is not in the "
                    "4-class admission whitelist"
                ) from exc
        if not isinstance(card.admission_class, AdmissionClass):
            raise FounderFirewallDenyError(
                "FOUNDER_FIREWALL_DENY: invalid admission_class"
            )

        # 2. Proof-of-Exhaustion.
        if card.admission_class == AdmissionClass.CRITICAL_SERVICE_OUTAGE:
            if (
                not card.outage_probe_receipt
                or len(card.outage_probe_receipt.strip()) < 8
            ):
                raise FounderFirewallDenyError(
                    "FOUNDER_FIREWALL_DENY: CRITICAL_SERVICE_OUTAGE requires a "
                    "verifiable outage_probe_receipt"
                )
        else:
            if not card.poe_receipt_id or not card.consult_digest:
                raise FounderFirewallDenyError(
                    "FOUNDER_FIREWALL_DENY: missing Proof-of-Exhaustion "
                    "(poe_receipt_id + consult_digest)"
                )
            row = self._conn.execute(
                """
                SELECT 1 FROM exhaustion_receipts
                WHERE instruction_id = ? AND poe_receipt_id = ? AND consult_digest = ?
                """,
                (card.instruction_id, card.poe_receipt_id, card.consult_digest),
            ).fetchone()
            if row is None:
                raise FounderFirewallDenyError(
                    "FOUNDER_FIREWALL_DENY: unverified or forged Proof-of-Exhaustion receipts"
                )

        # 3. The structured five-field contract.
        if (
            not card.deadlock_summary.strip()
            or "\n" in card.deadlock_summary
            or len(card.deadlock_summary) > 160
        ):
            raise FounderFirewallDenyError(
                "FOUNDER_FIREWALL_DENY: deadlock_summary must be a single line <= 160 chars"
            )
        if (
            not card.autonomy_stop_reason.strip()
            or len(card.autonomy_stop_reason) > 300
        ):
            raise FounderFirewallDenyError(
                "FOUNDER_FIREWALL_DENY: autonomy_stop_reason must be concise (1..300 chars)"
            )
        if not (2 <= len(card.options) <= 3):
            raise FounderFirewallDenyError(
                "FOUNDER_FIREWALL_DENY: card must offer 2 to 3 bounded options"
            )
        option_ids = [o.option_id for o in card.options]
        if len(set(option_ids)) != len(option_ids):
            raise FounderFirewallDenyError(
                "FOUNDER_FIREWALL_DENY: duplicate option IDs"
            )
        if card.recommended_option_id not in option_ids:
            raise FounderFirewallDenyError(
                "FOUNDER_FIREWALL_DENY: recommended_option_id must match one of the bounded options"
            )

        # 4. One-tap tokens, and enqueue with the coalescing policy.
        card_seed = (
            f"{card.instruction_id}|{card.base_sha}|{card.admission_class.value}|{ts}"
        ).encode("utf-8")
        card_id = "dec_" + hashlib.sha256(card_seed).hexdigest()[:14]
        tokens = {
            f"APPROVE_{opt.option_id}": f"tap:{card_id}:{opt.option_id}"
            for opt in card.options
        }
        tokens["REJECT_PARK"] = f"tap:{card_id}:REJECT_PARK"

        delivery_mode = (
            "IMMEDIATE_ALERT"
            if card.admission_class == AdmissionClass.CRITICAL_SERVICE_OUTAGE
            else "COALESCED_DIGEST"
        )
        serializable_card = {
            **asdict(card),
            "admission_class": card.admission_class.value,
            "options": [asdict(o) for o in card.options],
        }
        self._conn.execute(
            """
            INSERT INTO founder_decision_queue (
                card_id, instruction_id, admission_class, delivery_mode,
                card_json, one_tap_tokens_json, dispatched, created_at_epoch
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(card_id) DO UPDATE SET
                card_json = excluded.card_json,
                one_tap_tokens_json = excluded.one_tap_tokens_json
            """,
            (
                card_id,
                card.instruction_id,
                card.admission_class.value,
                delivery_mode,
                json.dumps(serializable_card, sort_keys=True),
                json.dumps(tokens, sort_keys=True),
                1 if delivery_mode == "IMMEDIATE_ALERT" else 0,
                ts,
            ),
        )

        # 5. The defect ratchet: a founder decision outside a guarded-path seal is a
        #    defect in the automation that should have made it unnecessary.
        defect_logged = False
        if card.admission_class != AdmissionClass.GUARDED_PATH_SEAL:
            self._conn.execute(
                """
                INSERT INTO founder_defect_ratchet (
                    card_id, instruction_id, admission_class,
                    missing_automation_reason, recorded_at_epoch
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    card_id,
                    card.instruction_id,
                    card.admission_class.value,
                    card.autonomy_stop_reason,
                    ts,
                ),
            )
            defect_logged = True

        return AdmittedDecision(
            card_id=card_id,
            delivery_mode=delivery_mode,
            one_tap_tokens=tokens,
            defect_logged=defect_logged,
        )

    def flush_coalesced_digest(self) -> list:
        """Return the queued non-outage cards as one batch and mark them dispatched."""
        rows = self._conn.execute(
            """
            SELECT card_id, card_json, one_tap_tokens_json
            FROM founder_decision_queue
            WHERE delivery_mode = 'COALESCED_DIGEST' AND dispatched = 0
            ORDER BY created_at_epoch ASC
            """
        ).fetchall()
        digest = [
            {
                "card_id": r[0],
                "card": json.loads(r[1]),
                "one_tap_tokens": json.loads(r[2]),
            }
            for r in rows
        ]
        if rows:
            self._conn.execute(
                "UPDATE founder_decision_queue SET dispatched = 1 "
                "WHERE delivery_mode = 'COALESCED_DIGEST' AND dispatched = 0"
            )
        return digest

    def defect_ratchet_entries(self) -> list:
        rows = self._conn.execute(
            """
            SELECT card_id, instruction_id, admission_class,
                   missing_automation_reason, recorded_at_epoch
            FROM founder_defect_ratchet ORDER BY id ASC
            """
        ).fetchall()
        return [
            {
                "card_id": r[0],
                "instruction_id": r[1],
                "admission_class": r[2],
                "missing_automation_reason": r[3],
                "recorded_at_epoch": r[4],
            }
            for r in rows
        ]

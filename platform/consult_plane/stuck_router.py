"""Compulsory stuck-state routing, owned by the System Reconciler (IoC).

Agents do not decide when to consult. The harness freezes an agent's execution
loop and routes it here when one of three deterministic triggers fires:

  1. REPEAT_ERROR_HASH   -- the same normalized stderr digest twice in one lane.
  2. ZERO_PROGRESS_CHURN -- 3 consecutive passes with no net reduction in
                             failing assertions.
  3. GATE_REFUSAL        -- a deterministic check (estate-gate, guarded-paths,
                             claim-gate) refused the lane.

A frozen lane may not retry until a consult-plane receipt unfreezes it. That is
the whole point: a stuck agent burns budget by trying again, so the retry is
refused mechanically rather than by advice.

Standard library only.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from dataclasses import dataclass
from typing import Optional


class LaneFrozenForConsultError(RuntimeError):
    """Raised when an agent attempts unconsulted retries while frozen."""


@dataclass(frozen=True)
class StuckVerdict:
    instruction_id: str
    is_stuck: bool
    trigger: Optional[
        str
    ]  # REPEAT_ERROR_HASH | ZERO_PROGRESS_CHURN | GATE_REFUSAL | None
    reason: str
    frozen: bool


def normalize_error_digest(stderr_text: str) -> str:
    """Normalize volatile paths, timestamps and line numbers into a stable digest.

    Two failures that differ only in where they were run are the SAME failure,
    and must freeze the lane rather than let the agent burn budget on them.
    """
    lines = [
        " ".join(line.strip().split())
        for line in stderr_text.strip().splitlines()
        if line.strip()
    ]
    canonical = "\n".join(lines[:20]).lower()
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


class StuckStateRouter:
    """System-owned compulsory stuck detector (IoC)."""

    def __init__(
        self,
        db_path: str = ":memory:",
        repeat_error_threshold: int = 2,
        zero_progress_threshold: int = 3,
    ) -> None:
        self.repeat_error_threshold = repeat_error_threshold
        self.zero_progress_threshold = zero_progress_threshold
        self._conn = sqlite3.connect(db_path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS lane_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instruction_id TEXT NOT NULL,
                error_digest TEXT NOT NULL,
                failing_assertions INTEGER NOT NULL,
                gate_refused INTEGER NOT NULL DEFAULT 0,
                gate_name TEXT,
                created_at_epoch INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS frozen_lanes (
                instruction_id TEXT PRIMARY KEY,
                trigger TEXT NOT NULL,
                reason TEXT NOT NULL,
                frozen_at_epoch INTEGER NOT NULL
            );
            """
        )

    def is_frozen(self, instruction_id: str):
        row = self._conn.execute(
            "SELECT trigger, reason FROM frozen_lanes WHERE instruction_id = ?",
            (instruction_id,),
        ).fetchone()
        return (str(row[0]), str(row[1])) if row else None

    def record_attempt(
        self,
        instruction_id: str,
        stderr_text: str,
        failing_assertions: int,
        gate_refused: bool = False,
        gate_name: Optional[str] = None,
        now_epoch: Optional[int] = None,
    ) -> StuckVerdict:
        """Record one attempt and decide whether the lane must now consult."""
        ts = now_epoch if now_epoch is not None else int(time.time())
        already_frozen = self.is_frozen(instruction_id)
        if already_frozen is not None:
            raise LaneFrozenForConsultError(
                f"COMPULSORY_CONSULT_REQUIRED: lane {instruction_id} is frozen "
                f"({already_frozen[0]}: {already_frozen[1]}). "
                "Agent may not retry without a verified consult-plane receipt."
            )

        err_digest = normalize_error_digest(stderr_text)
        self._conn.execute(
            """
            INSERT INTO lane_attempts (
                instruction_id, error_digest, failing_assertions,
                gate_refused, gate_name, created_at_epoch
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                instruction_id,
                err_digest,
                failing_assertions,
                1 if gate_refused else 0,
                gate_name,
                ts,
            ),
        )

        # Trigger 3: a deterministic gate refusal freezes immediately.
        if gate_refused:
            reason = f"Deterministic gate '{gate_name or 'unknown'}' refused lane"
            return self._freeze(instruction_id, "GATE_REFUSAL", reason, ts)

        # Trigger 1: the same normalized error digest seen twice in one lane.
        same_count = self._conn.execute(
            "SELECT COUNT(*) FROM lane_attempts WHERE instruction_id = ? AND error_digest = ?",
            (instruction_id, err_digest),
        ).fetchone()[0]
        if same_count >= self.repeat_error_threshold:
            reason = f"Error digest {err_digest} repeated {same_count} times"
            return self._freeze(instruction_id, "REPEAT_ERROR_HASH", reason, ts)

        # Trigger 2: three consecutive attempts with no net reduction in failures.
        recent = self._conn.execute(
            """
            SELECT failing_assertions FROM lane_attempts
            WHERE instruction_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (instruction_id, self.zero_progress_threshold),
        ).fetchall()
        if len(recent) >= self.zero_progress_threshold:
            counts = [int(r[0]) for r in reversed(recent)]  # oldest -> newest
            if counts[-1] > 0 and all(
                counts[i] >= counts[i - 1] for i in range(1, len(counts))
            ):
                reason = (
                    f"Zero progress across {len(counts)} attempts "
                    f"(failing_assertions={counts})"
                )
                return self._freeze(instruction_id, "ZERO_PROGRESS_CHURN", reason, ts)

        return StuckVerdict(
            instruction_id=instruction_id,
            is_stuck=False,
            trigger=None,
            reason="Progressing normally",
            frozen=False,
        )

    def _freeze(
        self, instruction_id: str, trigger: str, reason: str, ts: int
    ) -> StuckVerdict:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO frozen_lanes (instruction_id, trigger, reason, frozen_at_epoch)
            VALUES (?, ?, ?, ?)
            """,
            (instruction_id, trigger, reason, ts),
        )
        return StuckVerdict(
            instruction_id=instruction_id,
            is_stuck=True,
            trigger=trigger,
            reason=reason,
            frozen=True,
        )

    def unfreeze_after_consult(self, instruction_id: str, consult_digest: str) -> None:
        """Release a frozen lane. A consult digest is required: no digest, no release."""
        if not consult_digest.strip():
            raise ValueError("consult_digest is required to unfreeze a stuck lane")
        self._conn.execute(
            "DELETE FROM frozen_lanes WHERE instruction_id = ?", (instruction_id,)
        )
        self._conn.execute(
            "DELETE FROM lane_attempts WHERE instruction_id = ?", (instruction_id,)
        )

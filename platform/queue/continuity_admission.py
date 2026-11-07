"""Constrained capacity selection and transactional lease admission for the existing queue.

This module is a broker-side primitive, NOT a new scheduler or a claim that all
estate writes are mediated. The caller must authenticate actors, validate worker
telemetry, and enforce authorize_effect at EVERY mutation boundary. SQLite
must live on a durable single-writer broker; it is not a distributed consensus DB.

One mission retains its work item and epoch across worker crashes. Zombie writes
are refused only at mediated effect doors; unmediated credentials remain exposed.
"""
from __future__ import annotations

import math
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterable, FrozenSet, Optional, Tuple


class Refused(RuntimeError):
    """A non-authorized continuity transition; never implicitly recover by bypass."""


@dataclass(frozen=True)
class WorkerOffer:
    worker_id: str
    failure_domain: str
    capabilities: FrozenSet[str]
    authenticated: bool
    observed_at: float  # server observation time, not client wall-clock
    available_slots: int
    quota_available: bool
    context_tokens_available: int
    estimated_cost: float
    p95_latency_ms: float
    completion_rate: float  # measured on comparable tasks, 0..1


@dataclass(frozen=True)
class Requirement:
    capabilities: FrozenSet[str]
    max_cost: float
    min_context_tokens: int
    previous_failure_domain: str = ""
    max_observation_age_seconds: float = 120.0


def _finite(value: float) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def eligible(offer: WorkerOffer, req: Requirement, now: float) -> Tuple[bool, str]:
    """Fail closed on unobserved capacity, missing authority, stale or bad evidence."""
    if not offer.worker_id or not offer.failure_domain or not offer.authenticated:
        return False, "UNAUTHENTICATED_OFFER"
    if not _finite(now) or not _finite(offer.observed_at) or not _finite(req.max_observation_age_seconds):
        return False, "INVALID_TIME"
    age = now - offer.observed_at
    if age < 0 or age > req.max_observation_age_seconds or req.max_observation_age_seconds <= 0:
        return False, "STALE_OR_FUTURE_OFFER"
    if offer.available_slots < 1 or not offer.quota_available:
        return False, "NO_AVAILABLE_CAPACITY"
    if offer.context_tokens_available < req.min_context_tokens or req.min_context_tokens < 0:
        return False, "INSUFFICIENT_CONTEXT"
    if not req.capabilities.issubset(offer.capabilities):
        return False, "MISSING_CAPABILITY"
    if not all(_finite(v) for v in (req.max_cost, offer.estimated_cost, offer.p95_latency_ms, offer.completion_rate)):
        return False, "INVALID_METRICS"
    if (offer.estimated_cost < 0 or offer.estimated_cost > req.max_cost or
            offer.p95_latency_ms < 0 or not 0 <= offer.completion_rate <= 1):
        return False, "BUDGET_OR_METRICS_REFUSAL"
    return True, "ELIGIBLE"


def select_worker(offers: Iterable[WorkerOffer], req: Requirement, now: float,
                  excluded_workers: FrozenSet[str] = frozenset()) -> Optional[WorkerOffer]:
    """Choose a verified eligible worker, preferring independent failure domains.

    Ranking is deterministic and lexicographic, not an invented 0-100 AI score.
    Security, budget and capability constraints are hard filters before ranking.
    """
    candidates = [offer for offer in offers if offer.worker_id not in excluded_workers
                  and eligible(offer, req, now)[0]]
    if not candidates:
        return None
    return sorted(candidates, key=lambda w: (
        -(1 if req.previous_failure_domain and w.failure_domain != req.previous_failure_domain else 0),
        -w.completion_rate, w.p95_latency_ms, w.estimated_cost, w.worker_id
    ))[0]


class LeaseStore:
    """Use existing queue.db; BEGIN IMMEDIATE serializes claims on this broker.

    now must be trusted broker time. Fencing is only safe for side effects that
    call authorize_effect immediately before dispatch and honor its verdict.
    """

    def __init__(self, path: str):
        self.path = path
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS continuity_effects (
                mission_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                worker_id TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('PENDING','CONFIRMED')),
                receipt_sha256 TEXT,
                PRIMARY KEY(mission_id, action_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS continuity_leases (
                mission_id TEXT PRIMARY KEY,
                worker_id TEXT NOT NULL,
                epoch INTEGER NOT NULL CHECK(epoch > 0),
                expires_at REAL NOT NULL,
                last_observed REAL NOT NULL,
                progress_sequence INTEGER NOT NULL DEFAULT 0,
                checkpoint_sha256 TEXT,
                checkpoint_uri TEXT
            )""")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=10000")
            yield db
        finally:
            db.close()

    @staticmethod
    def _validate(worker: str, now: float, ttl: float):
        if not worker or not _finite(now) or not _finite(ttl) or ttl <= 0:
            raise Refused("INVALID_LEASE_REQUEST")

    def claim(self, mission_id: str, worker: str, now: float, ttl: float) -> int:
        """Transfer only an expired lease; increment epoch atomically.

        First acquisition returns 1. An unexpired holder, including the same worker,
        must heartbeat rather than issue itself a new token.
        """
        self._validate(worker, now, ttl)
        if not mission_id:
            raise Refused("MISSING_MISSION_ID")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT epoch,expires_at,last_observed FROM continuity_leases WHERE mission_id=?",
                             (mission_id,)).fetchone()
            if row and now < row[2]:
                raise Refused("CLOCK_REGRESSION")
            if row and now < row[1]:
                raise Refused("ACTIVE_OWNER")
            epoch = row[0] + 1 if row else 1
            if row:
                db.execute("""UPDATE continuity_leases SET worker_id=?,epoch=?,expires_at=?,
                    last_observed=?,progress_sequence=0 WHERE mission_id=?""",
                    (worker, epoch, now + ttl, now, mission_id))
            else:
                db.execute("""INSERT INTO continuity_leases
                    (mission_id,worker_id,epoch,expires_at,last_observed)
                    VALUES(?,?,?,?,?)""", (mission_id, worker, epoch, now + ttl, now))
            db.execute("COMMIT")
            return epoch

    def heartbeat(self, mission_id: str, worker: str, epoch: int, now: float,
                  ttl: float, sequence: int, checkpoint_sha256: Optional[str] = None,
                  checkpoint_uri: Optional[str] = None) -> None:
        self._validate(worker, now, ttl)
        if sequence < 0 or (checkpoint_sha256 is None) != (checkpoint_uri is None):
            raise Refused("BAD_CHECKPOINT")
        if checkpoint_sha256 is not None and (
                len(checkpoint_sha256) != 64 or any(c not in '0123456789abcdef' for c in checkpoint_sha256)
                or not checkpoint_uri.startswith('oci://')):
            raise Refused("BAD_CHECKPOINT")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT worker_id,epoch,expires_at,last_observed,progress_sequence
                FROM continuity_leases WHERE mission_id=?""", (mission_id,)).fetchone()
            if row is None or row[0] != worker or row[1] != epoch or now >= row[2]:
                raise Refused("STALE_FENCING_LEASE")
            if now < row[3] or sequence <= row[4]:
                raise Refused("REPLAY_OR_CLOCK_REGRESSION")
            db.execute("""UPDATE continuity_leases SET expires_at=?,last_observed=?,
                progress_sequence=?, checkpoint_sha256=COALESCE(?,checkpoint_sha256),
                checkpoint_uri=COALESCE(?,checkpoint_uri)
                WHERE mission_id=? AND worker_id=? AND epoch=?""",
                (now + ttl, now, sequence, checkpoint_sha256, checkpoint_uri,
                 mission_id, worker, epoch))
            db.execute("COMMIT")

    def authorize_effect(self, mission_id: str, worker: str, epoch: int,
                         now: float) -> None:
        if not _finite(now):
            raise Refused("INVALID_TIME")
        with self._connect() as db:
            row = db.execute("""SELECT worker_id,epoch,expires_at,last_observed
                FROM continuity_leases WHERE mission_id=?""", (mission_id,)).fetchone()
        if (row is None or row[0] != worker or row[1] != epoch or
                now >= row[2] or now < row[3]):
            raise Refused("STALE_FENCING_LEASE")

    def reserve_effect(self, mission_id: str, action_id: str, worker: str,
                       epoch: int, now: float) -> None:
        """Atomically reserve a mediated side effect; the lease alone is not authorization.

        External effects must pass the existing action-door DoF/policy checks.
        A PENDING record after crash requires independent reconciliation, not replay.
        """
        if not mission_id or not action_id or not worker or not isinstance(epoch, int):
            raise Refused("INVALID_EFFECT_REQUEST")
        if not _finite(now):
            raise Refused("INVALID_TIME")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT worker_id,epoch,expires_at,last_observed FROM continuity_leases "
                "WHERE mission_id=?", (mission_id,),
            ).fetchone()
            if (row is None or row[0] != worker or row[1] != epoch or
                    now >= row[2] or now < row[3]):
                raise Refused("STALE_FENCING_LEASE")
            existing = db.execute(
                "SELECT state FROM continuity_effects WHERE mission_id=? AND action_id=?",
                (mission_id, action_id),
            ).fetchone()
            if existing is not None:
                raise Refused("ALREADY_CONFIRMED" if existing[0] == "CONFIRMED"
                              else "PENDING_RECONCILIATION_REQUIRED")
            db.execute(
                "INSERT INTO continuity_effects "
                "(mission_id,action_id,worker_id,epoch,state) VALUES(?,?,?,?,'PENDING')",
                (mission_id, action_id, worker, epoch),
            )
            db.execute("COMMIT")

    def confirm_effect(self, mission_id: str, action_id: str, worker: str,
                       epoch: int, now: float, receipt_sha256: str,
                       *, verified_by_independent_broker: bool = False) -> None:
        """Record outcome only after a distinct trusted effect-sink verifier confirms.

        The broker flag MUST be assigned by server code, never forwarded from
        a user request, a model output, or an untrusted browser.
        """
        if not verified_by_independent_broker:
            raise Refused("INDEPENDENT_PROOF_REQUIRED")
        if (len(receipt_sha256) != 64 or
                any(x not in "0123456789abcdef" for x in receipt_sha256)):
            raise Refused("INVALID_RECEIPT_DIGEST")
        if not _finite(now):
            raise Refused("INVALID_TIME")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            owner = db.execute(
                "SELECT worker_id,epoch,expires_at,last_observed FROM continuity_leases "
                "WHERE mission_id=?", (mission_id,),
            ).fetchone()
            if (owner is None or owner[0] != worker or owner[1] != epoch or
                    now >= owner[2] or now < owner[3]):
                raise Refused("STALE_FENCING_LEASE")
            reserved = db.execute(
                "SELECT worker_id,epoch,state FROM continuity_effects "
                "WHERE mission_id=? AND action_id=?", (mission_id, action_id),
            ).fetchone()
            if (reserved is None or reserved[0] != worker or reserved[1] != epoch
                    or reserved[2] != "PENDING"):
                raise Refused("EFFECT_NOT_RESERVED_BY_OWNER")
            db.execute(
                "UPDATE continuity_effects SET state='CONFIRMED',receipt_sha256=? "
                "WHERE mission_id=? AND action_id=?",
                (receipt_sha256, mission_id, action_id),
            )
            db.execute("COMMIT")

    def effect_snapshot(self, mission_id: str, action_id: str):
        with self._connect() as db:
            return db.execute(
                "SELECT worker_id,epoch,state,receipt_sha256 FROM continuity_effects "
                "WHERE mission_id=? AND action_id=?", (mission_id, action_id),
            ).fetchone()

    def snapshot(self, mission_id: str):
        with self._connect() as db:
            return db.execute("""SELECT worker_id,epoch,expires_at,checkpoint_sha256,checkpoint_uri
                FROM continuity_leases WHERE mission_id=?""", (mission_id,)).fetchone()

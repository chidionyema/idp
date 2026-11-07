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
import json
import hashlib
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

    def __init__(self, path: str, *, receipt_verifier=None):
        self.path = path
        # Supplied ONLY by an independently authenticated broker; no verifier
        # means effect confirmation is refused, never accepted by default.
        self._receipt_verifier = receipt_verifier
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
                       *, receipt_proof: bytes = b"") -> None:
        """Record only an independently verified, manifest-bound receipt.

        The verifier is provisioned by trusted server startup; it MUST verify
        an exact signed action/actor/epoch/result manifest. Model or browser
        inputs cannot set a Boolean to mint certifier authority.
        """
        if self._receipt_verifier is None or not callable(self._receipt_verifier):
            raise Refused("INDEPENDENT_PROOF_REQUIRED")
        if (len(receipt_sha256) != 64 or
                any(x not in "0123456789abcdef" for x in receipt_sha256)):
            raise Refused("INVALID_RECEIPT_DIGEST")
        if not _finite(now):
            raise Refused("INVALID_TIME")
        message = (f"genesis.effect.v1\n{mission_id}\n{action_id}\n{worker}\n"
                   f"{epoch}\n{receipt_sha256}\n").encode("utf-8")
        try:
            verified = (isinstance(receipt_proof, bytes) and
                        bool(self._receipt_verifier(message, receipt_proof)))
        except Exception:
            verified = False
        if not verified:
            raise Refused("INVALID_INDEPENDENT_RECEIPT")
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


class HeartbeatRegistry:
    """Store broker-observed worker liveness and provenance-qualified capacity.

    Not an ingress authenticator: trusted_actor and capacity_source MUST be
    assigned by the independently authenticated server, not accepted as client
    fields. A browser demo is not a live source. A missing web-agent relay
    leaves capacity UNKNOWN rather than fabricating presence.
    """

    def __init__(self, path: str):
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS continuity_worker_beats (
                worker_id TEXT PRIMARY KEY,
                principal TEXT NOT NULL,
                adapter TEXT NOT NULL,
                provider TEXT NOT NULL,
                host TEXT NOT NULL,
                failure_domain TEXT NOT NULL,
                capabilities TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                last_seen REAL NOT NULL,
                progress_seen REAL,
                progress_digest TEXT,
                available_slots INTEGER NOT NULL,
                quota_available INTEGER NOT NULL,
                context_tokens INTEGER NOT NULL,
                estimated_cost REAL NOT NULL,
                p95_latency_ms REAL NOT NULL,
                completion_rate REAL NOT NULL,
                capacity_source TEXT NOT NULL,
                capacity_evidence TEXT NOT NULL
            )""")

    def observe(self, offer: WorkerOffer, *, trusted_actor: str,
                broker_now: float, sequence: int, adapter: str, provider: str,
                host: str, capacity_source: str, capacity_evidence: str,
                progress_digest: Optional[str] = None) -> None:
        if (not trusted_actor or trusted_actor != offer.worker_id or
                not offer.authenticated):
            raise Refused("UNAUTHENTICATED_HEARTBEAT")
        if (not adapter or not provider or not host or not capacity_evidence or
                capacity_source not in ("provider_api", "authenticated_runtime", "unknown")):
            raise Refused("INVALID_HEARTBEAT_PROVENANCE")
        if not _finite(broker_now) or offer.observed_at != broker_now or sequence <= 0:
            raise Refused("UNTRUSTED_CLOCK_OR_SEQUENCE")
        if (not offer.failure_domain or offer.available_slots < 0 or
                offer.context_tokens_available < 0 or
                not all(_finite(x) for x in (offer.estimated_cost, offer.p95_latency_ms,
                                              offer.completion_rate)) or
                offer.estimated_cost < 0 or offer.p95_latency_ms < 0 or
                not 0 <= offer.completion_rate <= 1):
            raise Refused("INVALID_CAPACITY_METRICS")
        if progress_digest is not None and (
                len(progress_digest) != 64 or
                any(c not in "0123456789abcdef" for c in progress_digest)):
            raise Refused("INVALID_PROGRESS_DIGEST")
        with sqlite3.connect(self.path, timeout=15, isolation_level=None) as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT principal,sequence,last_seen,progress_digest,progress_seen "
                "FROM continuity_worker_beats WHERE worker_id=?",
                (offer.worker_id,),
            ).fetchone()
            if old is not None:
                if old[0] != trusted_actor:
                    raise Refused("WORKER_IDENTITY_CHANGED")
                if sequence <= old[1] or broker_now < old[2]:
                    raise Refused("HEARTBEAT_REPLAY_OR_CLOCK_REGRESSION")
            last_digest = old[3] if old else None
            progress_seen = old[4] if old else None
            if progress_digest is not None and progress_digest != last_digest:
                last_digest, progress_seen = progress_digest, broker_now
            db.execute("""INSERT INTO continuity_worker_beats
                (worker_id,principal,adapter,provider,host,failure_domain,
                 capabilities,sequence,last_seen,progress_seen,progress_digest,
                 available_slots,quota_available,context_tokens,estimated_cost,
                 p95_latency_ms,completion_rate,capacity_source,capacity_evidence)
                 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(worker_id) DO UPDATE SET
                   adapter=excluded.adapter,provider=excluded.provider,
                   host=excluded.host,failure_domain=excluded.failure_domain,
                   capabilities=excluded.capabilities,sequence=excluded.sequence,
                   last_seen=excluded.last_seen,progress_seen=excluded.progress_seen,
                   progress_digest=excluded.progress_digest,
                   available_slots=excluded.available_slots,
                   quota_available=excluded.quota_available,
                   context_tokens=excluded.context_tokens,
                   estimated_cost=excluded.estimated_cost,
                   p95_latency_ms=excluded.p95_latency_ms,
                   completion_rate=excluded.completion_rate,
                   capacity_source=excluded.capacity_source,
                   capacity_evidence=excluded.capacity_evidence""",
                (offer.worker_id, trusted_actor, adapter, provider, host,
                 offer.failure_domain, json.dumps(sorted(offer.capabilities)),
                 sequence, broker_now, progress_seen, last_digest,
                 offer.available_slots, int(offer.quota_available),
                 offer.context_tokens_available, offer.estimated_cost,
                 offer.p95_latency_ms, offer.completion_rate, capacity_source,
                 capacity_evidence),
            )
            db.execute("COMMIT")

    def observed(self, now: float, *, ttl: float = 90,
                 max_progress_age: float = 300,
                 expected_workers: Iterable[str] = ()) -> dict:
        """Classify UNKNOWN, PROVISIONAL, STALLED, EXHAUSTED and READY distinctly.

        Only READY workers expose capacity to security-critical scheduling.
        An authenticated heartbeat is liveness, not proof mission progress.
        """
        if not _finite(now) or not _finite(ttl) or not _finite(max_progress_age) or ttl <= 0:
            raise Refused("INVALID_OBSERVATION_WINDOW")
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            rows = db.execute("SELECT * FROM continuity_worker_beats").fetchall()
        out = {wid: {"status": "UNKNOWN", "offer": None,
                     "reason": "no authenticated heartbeat"} for wid in expected_workers}
        for row in rows:
            offer = WorkerOffer(
                row["worker_id"], row["failure_domain"],
                frozenset(json.loads(row["capabilities"])), True,
                row["last_seen"], row["available_slots"],
                bool(row["quota_available"]), row["context_tokens"],
                row["estimated_cost"], row["p95_latency_ms"],
                row["completion_rate"])
            if now < row["last_seen"] or now - row["last_seen"] > ttl:
                status, reason = "UNKNOWN", "heartbeat stale or clock regressed"
            elif row["available_slots"] < 1 or not row["quota_available"]:
                status, reason = "EXHAUSTED", "no verified slots or quota"
            elif (row["progress_seen"] is not None and
                    now - row["progress_seen"] > max_progress_age):
                status, reason = "STALLED", "heartbeat continues without progress"
            elif row["capacity_source"] == "provider_api":
                status, reason = "READY", "provider capacity receipt"
            else:
                status, reason = "PROVISIONAL", "no independent provider capacity proof"
            out[row["worker_id"]] = {
                "status": status, "offer": offer if status == "READY" else None,
                "reason": reason, "last_seen": row["last_seen"],
                "sequence": row["sequence"],
                "progress_seen": row["progress_seen"],
                "capacity_evidence": row["capacity_evidence"],
                "provider": row["provider"],
                "host": row["host"],
            }
        return out


def restore_verified_checkpoint(uri: str, digest_sha256: str, read_ciphertext,
                                *, max_ciphertext_bytes: int = 2 * 1024 * 1024) -> bytes:
    """Read ciphertext from a governed off-host client and verify exact bytes.

    This proves byte integrity ONLY. Encryption/key isolation, object existence,
    and decrypted mission content's semantic correctness require separate proof.
    """
    if (not isinstance(uri, str) or not uri.startswith("oci://") or
            not isinstance(digest_sha256, str) or len(digest_sha256) != 64 or
            any(x not in "0123456789abcdef" for x in digest_sha256)):
        raise Refused("INVALID_CHECKPOINT_REFERENCE")
    if not callable(read_ciphertext):
        raise Refused("NO_VERIFIED_CHECKPOINT_READER")
    try:
        contents = read_ciphertext(uri)
    except Exception as exc:
        raise Refused("CHECKPOINT_READ_FAILED") from exc
    if (not isinstance(contents, bytes) or len(contents) < 1 or
            len(contents) > max_ciphertext_bytes):
        raise Refused("CHECKPOINT_UNAVAILABLE_OR_OVERSIZE")
    if hashlib.sha256(contents).hexdigest() != digest_sha256:
        raise Refused("CHECKPOINT_DIGEST_MISMATCH")
    return contents


def attempt_verified_takeover(mission_id: str, lease_store: LeaseStore,
                              beats: HeartbeatRegistry, req: Requirement,
                              now: float, ttl: float, read_ciphertext) -> dict:
    """Claim a capable worker for a lost mission without dispatching unverified code.

    A trusted caller must validate decrypted mission content and DoF scope
    before invoking the existing dispatcher. OWNED never means OPERATING.
    LeaseStore's transaction prevents concurrent supervisors double-claiming.
    """
    if not mission_id or not _finite(now) or not _finite(ttl) or ttl <= 0:
        raise Refused("INVALID_TAKEOVER_REQUEST")
    previous = lease_store.snapshot(mission_id)
    if previous is None:
        return {"state": "RECOVERY_PENDING", "reason": "MISSING_MISSION_LEASE"}
    old_worker, _old_epoch, expires_at, digest, uri = previous
    if now < expires_at:
        return {"state": "RECOVERY_PENDING", "reason": "OWNER_LEASE_STILL_ACTIVE"}
    if not digest or not uri:
        return {"state": "RECOVERY_PENDING", "reason": "NO_DURABLE_CHECKPOINT"}
    try:
        restored = restore_verified_checkpoint(uri, digest, read_ciphertext)
    except Refused as exc:
        return {"state": "RECOVERY_PENDING", "reason": str(exc)}
    observed = beats.observed(now)
    offers = [row["offer"] for row in observed.values()
              if row["status"] == "READY" and row["offer"] is not None]
    selected = select_worker(offers, req, now, frozenset({old_worker}))
    if selected is None:
        return {"state": "RECOVERY_PENDING", "reason": "NO_ELIGIBLE_CAPACITY"}
    try:
        new_epoch = lease_store.claim(mission_id, selected.worker_id, now, ttl)
    except Refused as exc:
        return {"state": "RECOVERY_PENDING", "reason": str(exc)}
    with lease_store._connect() as db:
        pending_effects = [row[0] for row in db.execute(
            "SELECT action_id FROM continuity_effects "
            "WHERE mission_id=? AND state='PENDING' ORDER BY action_id", (mission_id,)
        )]
    return {
        "state": "OWNED", "worker_id": selected.worker_id,
        "lease_epoch": new_epoch,
        "checkpoint_uri": uri, "checkpoint_sha256": digest,
        "checkpoint_bytes_verified": len(restored),
        "pending_effects_requiring_reconciliation": pending_effects,
        "requires_external_policy_and_decrypt_verification": True,
    }

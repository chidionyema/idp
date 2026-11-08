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

    def __init__(self, path: str, *, receipt_verifier=None, handover_verifier=None):
        self.path = path
        # Supplied ONLY by an independently authenticated broker; no verifier
        # means effect confirmation is refused, never accepted by default.
        self._receipt_verifier = receipt_verifier
        # Inject ONLY from a trusted broker; never accept a model-supplied flag.
        self._handover_verifier = handover_verifier
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


    def preemptive_handover(self, mission_id: str, old_worker: str,
                           old_epoch: int, new_worker: str, now: float,
                           ttl: float, checkpoint_sha256: str, checkpoint_uri: str,
                           *, handover_proof: bytes = b"") -> int:
        """Atomically fence an active owner after a trusted broker authorizes morph.

        Caller must first independently authenticate the destination, establish
        DoF eligibility and restore the encrypted checkpoint. This method
        enforces signed authorization AND compare-and-swap custody, not admission
        or semantic correctness. No proof verifier -> no proactive transfer.
        All real mutation doors must separately enforce the resulting epoch.
        """
        self._validate(new_worker, now, ttl)
        if (not mission_id or not old_worker or new_worker == old_worker or
                not isinstance(old_epoch, int) or isinstance(old_epoch, bool) or
                old_epoch <= 0 or not isinstance(checkpoint_sha256, str) or
                len(checkpoint_sha256) != 64 or
                any(c not in "0123456789abcdef" for c in checkpoint_sha256) or
                not isinstance(checkpoint_uri, str) or
                not checkpoint_uri.startswith("oci://")):
            raise Refused("INVALID_PREEMPTIVE_HANDOVER")
        verifier = getattr(self, "_handover_verifier", None)
        if not callable(verifier):
            raise Refused("INDEPENDENT_HANDOVER_PROOF_REQUIRED")
        # Bind approval to the precise old custody, new executor, stored
        # checkpoint and a bounded timestamp/TTL. Epoch CAS prevents replay.
        message = (f"genesis.morph.handover.v1\n{mission_id}\n{old_worker}\n"
                   f"{old_epoch}\n{new_worker}\n{checkpoint_sha256}\n"
                   f"{checkpoint_uri}\n{now:.6f}\n{ttl:.6f}\n").encode()
        try:
            approved = (type(handover_proof) is bytes and
                        bool(verifier(message, handover_proof)))
        except Exception:
            approved = False
        if not approved:
            raise Refused("INVALID_INDEPENDENT_HANDOVER_PROOF")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT worker_id,epoch,expires_at,last_observed,checkpoint_sha256,"
                "checkpoint_uri FROM continuity_leases WHERE mission_id=?",
                (mission_id,),
            ).fetchone()
            if (row is None or row[0] != old_worker or row[1] != old_epoch or
                    now < row[3] or now >= row[2]):
                raise Refused("STALE_FENCING_LEASE")
            if (row[4] != checkpoint_sha256 or row[5] != checkpoint_uri):
                raise Refused("CHECKPOINT_NOT_DURABLY_ACKNOWLEDGED")
            unresolved = db.execute(
                "SELECT 1 FROM continuity_effects WHERE mission_id=? "
                "AND state='PENDING' LIMIT 1", (mission_id,),
            ).fetchone()
            if unresolved:
                raise Refused("PENDING_RECONCILIATION_REQUIRED")
            next_epoch = old_epoch + 1
            db.execute(
                "UPDATE continuity_leases SET worker_id=?,epoch=?,expires_at=?,"
                "last_observed=?,progress_sequence=0 "
                "WHERE mission_id=? AND worker_id=? AND epoch=?",
                (new_worker, next_epoch, now + ttl, now, mission_id,
                 old_worker, old_epoch),
            )
            db.execute("COMMIT")
        return next_epoch

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
                              now: float, ttl: float, read_ciphertext,
                              decrypt_and_validate_checkpoint=None) -> dict:
    """Resume only from independently authenticated AND decrypted durable content.

    The ciphertext reader and decryptor must be separately provisioned by
    trusted broker startup. HTTP/model-controlled callbacks are NEVER trusted.
    The verifier must authenticate the fixed KMS key/mission-associated data
    and return a strict manifest with a full immutable source SHA.
    This function ONLY transfers custody: it neither dispatches a worker nor
    declares a mission operational. DoF and privileged effect checks remain
    mandatory at the real action door.
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
    if not callable(decrypt_and_validate_checkpoint):
        return {"state": "RECOVERY_PENDING", "reason": "AUTHENTICATED_DECRYPTOR_UNAVAILABLE"}
    try:
        ciphertext = restore_verified_checkpoint(uri, digest, read_ciphertext)
        manifest = decrypt_and_validate_checkpoint(mission_id, uri, ciphertext)
    except Refused as exc:
        return {"state": "RECOVERY_PENDING", "reason": str(exc)}
    except Exception:
        return {"state": "RECOVERY_PENDING", "reason": "CHECKPOINT_DECRYPT_OR_VALIDATION_FAILED"}
    if not isinstance(manifest, dict):
        return {"state": "RECOVERY_PENDING", "reason": "INVALID_DECRYPTED_MANIFEST"}
    source_sha = manifest.get("source_sha")
    if (manifest.get("mission_id") != mission_id or
            not isinstance(source_sha, str) or len(source_sha) != 40 or
            any(c not in "0123456789abcdef" for c in source_sha) or
            not isinstance(manifest.get("resume_cursor"), str) or
            not manifest["resume_cursor"] or
            manifest.get("schema") != "genesis.mission.checkpoint.v1"):
        return {"state": "RECOVERY_PENDING", "reason": "INVALID_DECRYPTED_MANIFEST"}

    observed = beats.observed(now)
    offers = [row["offer"] for row in observed.values()
              if row["status"] == "READY" and row["offer"] is not None]
    selected = select_worker(offers, req, now, frozenset({old_worker}))
    if selected is None:
        return {"state": "RECOVERY_PENDING", "reason": "NO_ELIGIBLE_CAPACITY"}
    with lease_store._connect() as db:
        pending_effects = [row[0] for row in db.execute(
            "SELECT action_id FROM continuity_effects "
            "WHERE mission_id=? AND state='PENDING' ORDER BY action_id", (mission_id,)
        )]
    try:
        new_epoch = lease_store.claim(mission_id, selected.worker_id, now, ttl)
    except Refused as exc:
        return {"state": "RECOVERY_PENDING", "reason": str(exc)}
    return {
        "state": "RECONCILIATION_REQUIRED" if pending_effects else "CUSTODY_TRANSFERRED",
        "worker_id": selected.worker_id,
        "lease_epoch": new_epoch,
        "source_sha": source_sha,
        "resume_cursor": manifest["resume_cursor"],
        "checkpoint_uri": uri, "checkpoint_sha256": digest,
        "checkpoint_bytes_verified": len(ciphertext),
        "pending_effects_requiring_reconciliation": pending_effects,
        "scope": "READ_AND_RECONCILE" if pending_effects else "PENDING_DOF_AUTHORIZATION",
        "runtime_dispatch_verified": False,
        "operationally_complete": False,
    }


# Genesis MORPH foundation, #7790: deterministic resource/runway evaluation only.
# This does NOT constitute a provider adapter, authorization gate or auto-scheduler.
# Trusted server adapters must bind every observation's principal and evidence.
MORPH_SCHEMA = "genesis.morph.risk.v1"
MORPH_PROVENANCE = frozenset(("provider_api", "authenticated_runtime",
                             "host_metrics", "trusted_supervisor"))
MORPH_STATES = ("HEALTHY", "PRESSURED", "AT_RISK", "CRITICAL", "UNKNOWN")


@dataclass(frozen=True)
class LifeSignal:
    """One broker-observed resource signal; missing values remain UNKNOWN."""
    resource: str
    observed_at: float
    provenance: str
    evidence_ref: str
    remaining_units: Optional[float] = None
    depletion_per_second: Optional[float] = None
    hard_deadline_at: Optional[float] = None
    failed: bool = False


@dataclass(frozen=True)
class MorphBudget:
    """Independent supervisor policy measurements, never model-supplied authority."""
    checkpoint_seconds: float
    destination_seconds: float
    restore_verify_seconds: float
    safety_margin_seconds: float
    max_signal_age_seconds: float = 120.0
    max_checkpoint_age_seconds: float = 300.0
    # Independently defined by the trusted runtime/admission profile.
    # Empty scope can never produce a trusted HEALTHY verdict.
    required_resources: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class MorphVerdict:
    schema: str
    state: str
    action: str
    reason_codes: Tuple[str, ...]
    runway_seconds: Optional[float]
    recovery_budget_seconds: float
    observed_resources: Tuple[str, ...]
    unknown_resources: Tuple[str, ...]
    permits_privileged_effects: bool = False  # a risk evaluator NEVER grants authority


def _metric(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def assess_morph_risk(signals: Iterable[LifeSignal], *,
                      now: float, budget: MorphBudget,
                      checkpoint_age_seconds: Optional[float],
                      previous_state: str = "UNKNOWN",
                      consecutive_clear_observations: int = 0) -> MorphVerdict:
    """Pure life/runway evaluation, with cautious UNKNOWN and hysteresis.

    This is decision support for the existing trusted supervisor. Signals,
    budget and time must be independently established outside the agent/model.
    The returned verdict never constitutes a DoF permit, a signed admission,
    or evidence that any checkpoint or morph actually occurred.
    """
    constraints = (budget.checkpoint_seconds, budget.destination_seconds,
                   budget.restore_verify_seconds, budget.safety_margin_seconds,
                   budget.max_signal_age_seconds, budget.max_checkpoint_age_seconds)
    if (not _metric(now) or any(not _metric(x) or x < 0 for x in constraints)
            or budget.max_signal_age_seconds <= 0
            or budget.max_checkpoint_age_seconds <= 0
            or (checkpoint_age_seconds is not None and
                (not _metric(checkpoint_age_seconds) or checkpoint_age_seconds < 0))
            or previous_state not in MORPH_STATES
            or type(consecutive_clear_observations) is not int
            or consecutive_clear_observations < 0):
        raise Refused("INVALID_MORPH_EVALUATION")
    total = sum(constraints[:4])
    if not math.isfinite(total) or total <= 0:
        raise Refused("INVALID_MORPH_RECOVERY_BUDGET")

    if (not isinstance(budget.required_resources, frozenset) or
            any(not isinstance(item, str) or not item.strip()
                for item in budget.required_resources)):
        raise Refused("INVALID_MORPH_RESOURCE_SCOPE")
    seen, unknown, reasons, runways = set(), set(), set(), []
    for signal in signals:
        if not isinstance(signal, LifeSignal) or not signal.resource:
            raise Refused("INVALID_MORPH_SIGNAL")
        if signal.resource in seen:
            raise Refused("DUPLICATE_MORPH_RESOURCE")
        seen.add(signal.resource)
        if (not _metric(signal.observed_at) or now < signal.observed_at or
                now - signal.observed_at > budget.max_signal_age_seconds or
                signal.provenance not in MORPH_PROVENANCE or
                not signal.evidence_ref):
            unknown.add(signal.resource)
            reasons.add("STALE_OR_UNTRUSTED_SIGNAL")
            continue
        if type(signal.failed) is not bool:
            raise Refused("INVALID_MORPH_SIGNAL")
        if signal.failed:
            runways.append(0.0)
            reasons.add("VERIFIED_RESOURCE_FAILURE")
            continue
        known = False
        if signal.remaining_units is not None or signal.depletion_per_second is not None:
            if (not _metric(signal.remaining_units) or
                    not _metric(signal.depletion_per_second) or
                    signal.remaining_units < 0 or signal.depletion_per_second < 0):
                unknown.add(signal.resource)
                reasons.add("INVALID_OR_INCOMPLETE_RUNWAY")
                continue
            if signal.depletion_per_second > 0:
                runways.append(signal.remaining_units / signal.depletion_per_second)
                known = True
            elif signal.remaining_units == 0:
                runways.append(0.0)
                known = True
            # Zero burn rate does not establish infinite future capacity.
        if signal.hard_deadline_at is not None:
            if not _metric(signal.hard_deadline_at):
                unknown.add(signal.resource)
                reasons.add("INVALID_DEADLINE")
                continue
            runways.append(max(0.0, signal.hard_deadline_at - now))
            known = True
        if not known:
            unknown.add(signal.resource)
            reasons.add("UNBOUNDED_OR_MISSING_RUNWAY")

    if not seen:
        reasons.add("NO_RESOURCE_TELEMETRY")
    if not budget.required_resources:
        unknown.add("_risk_profile")
        reasons.add("UNDECLARED_RESOURCE_COVERAGE")
    for missing in budget.required_resources - seen:
        unknown.add(missing)
        reasons.add("MISSING_REQUIRED_RESOURCE")
    runway = min(runways) if runways else None
    if runway is not None and runway <= budget.checkpoint_seconds:
        state = "CRITICAL"
        reasons.add("RECOVERY_RUNWAY_CRITICAL")
    elif runway is not None and runway <= total:
        state = "AT_RISK"
        reasons.add("RECOVERY_RUNWAY_INSUFFICIENT")
    elif runway is not None and runway <= 2 * total:
        state = "PRESSURED"
        reasons.add("RESOURCE_MARGIN_NARROWING")
    elif unknown or runway is None:
        state = "UNKNOWN"
    else:
        state = "HEALTHY"

    if state in ("HEALTHY", "PRESSURED") and unknown:
        state = "UNKNOWN"
        reasons.add("INSUFFICIENT_RESOURCE_COVERAGE")
    if checkpoint_age_seconds is None:
        reasons.add("NO_VERIFIED_CHECKPOINT")
        if state not in ("CRITICAL",):
            state = "AT_RISK"
    elif checkpoint_age_seconds > budget.max_checkpoint_age_seconds:
        reasons.add("CHECKPOINT_TOO_OLD")
        if state not in ("CRITICAL",):
            state = "AT_RISK"
    # Prevent a single healthy sample from cancelling an imminent morph:
    # callers must count independent trusted clear observations, not heartbeats.
    if (state == "HEALTHY" and previous_state in ("CRITICAL", "AT_RISK",
                                                    "PRESSURED") and
            consecutive_clear_observations < 2):
        state = "PRESSURED"
        reasons.add("WAITING_FOR_INDEPENDENT_CLEARANCE")

    action = {
        "HEALTHY": "CONTINUE",
        "PRESSURED": "PREPARE_DESTINATION",
        "AT_RISK": "CHECKPOINT_AND_MORPH",
        "CRITICAL": "STOP_RISKY_EFFECTS_AND_RECOVER",
        "UNKNOWN": "CHECKPOINT_AND_PROBE",
    }[state]
    return MorphVerdict(
        MORPH_SCHEMA, state, action, tuple(sorted(reasons)), runway, total,
        tuple(sorted(seen - unknown)), tuple(sorted(unknown)),
    )


def prepare_preemptive_morph(mission_id: str, lease_store: LeaseStore,
                             beats: HeartbeatRegistry, req: Requirement,
                             verdict: MorphVerdict, now: float,
                             read_ciphertext, decrypt_and_validate_checkpoint) -> dict:
    """Verify custody, checkpoint and alternate capacity BEFORE signing a handover.

    Only returns an *unsigned proposal*, never grants or rotates a lease.
    Trusted broker must recheck fresh state/DoF, authenticate a destination,
    sign the exact transfer and call LeaseStore.preemptive_handover.
    """
    if (not isinstance(verdict, MorphVerdict) or
            verdict.schema != MORPH_SCHEMA or verdict.state not in MORPH_STATES
            or not mission_id or not _metric(now)):
        raise Refused("INVALID_MORPH_PREPARATION")
    if verdict.state not in ("AT_RISK", "CRITICAL"):
        return {"state": "NOT_TRIGGERED", "reason": verdict.state}
    previous = lease_store.snapshot(mission_id)
    if previous is None:
        return {"state": "RECOVERY_PENDING", "reason": "MISSING_MISSION_LEASE"}
    old_worker, epoch, expires_at, digest, uri = previous
    if now >= expires_at:
        return {"state": "RECOVERY_PENDING", "reason": "LEASE_EXPIRED_USE_TAKEOVER"}
    if not digest or not uri:
        return {"state": "RECOVERY_PENDING", "reason": "NO_DURABLE_CHECKPOINT"}
    if not callable(decrypt_and_validate_checkpoint):
        return {"state": "RECOVERY_PENDING", "reason": "AUTHENTICATED_DECRYPTOR_UNAVAILABLE"}
    try:
        ciphertext = restore_verified_checkpoint(uri, digest, read_ciphertext)
        manifest = decrypt_and_validate_checkpoint(mission_id, uri, ciphertext)
    except Refused as exc:
        return {"state": "RECOVERY_PENDING", "reason": str(exc)}
    except Exception:
        return {"state": "RECOVERY_PENDING", "reason": "CHECKPOINT_DECRYPT_OR_VALIDATION_FAILED"}
    if (not isinstance(manifest, dict) or manifest.get("mission_id") != mission_id or
            manifest.get("schema") != "genesis.mission.checkpoint.v1" or
            not isinstance(manifest.get("source_sha"), str) or
            len(manifest["source_sha"]) != 40 or
            any(c not in "0123456789abcdef" for c in manifest["source_sha"]) or
            not isinstance(manifest.get("resume_cursor"), str) or
            not manifest["resume_cursor"]):
        return {"state": "RECOVERY_PENDING", "reason": "INVALID_DECRYPTED_MANIFEST"}
    with lease_store._connect() as db:
        pending = db.execute(
            "SELECT 1 FROM continuity_effects WHERE mission_id=? "
            "AND state='PENDING' LIMIT 1", (mission_id,),
        ).fetchone()
    if pending:
        return {"state": "RECOVERY_PENDING", "reason": "PENDING_RECONCILIATION_REQUIRED"}
    obs = beats.observed(now)
    offers = [row["offer"] for row in obs.values()
              if row["status"] == "READY" and row["offer"] is not None]
    selected = select_worker(offers, req, now, frozenset({old_worker}))
    if selected is None:
        return {"state": "RECOVERY_PENDING", "reason": "NO_ELIGIBLE_CAPACITY"}
    return {
        "state": "READY_FOR_SIGNED_HANDOVER", "mission_id": mission_id,
        "old_worker": old_worker, "old_epoch": epoch,
        "new_worker": selected.worker_id,
        "checkpoint_sha256": digest, "checkpoint_uri": uri,
        "source_sha": manifest["source_sha"], "resume_cursor": manifest["resume_cursor"],
        "runtime_dispatch_verified": False, "operationally_complete": False,
        "authorization_granted": False,
    }

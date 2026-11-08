"""Genesis MORPH execution adapter for the existing #7790 broker and Temporal runner.

No new scheduler, admission authority, credential store, event bus or control plane.
The only mutation here is a *broker-mediated* custody transition following real
checkpoint readback and a separately authorized, signed handover.

External runtime wires trusted observability, QUAD identity, DoF action-door,
durable workflow event sink and Temporal dispatch. Missing dependencies are a
truthful RECOVERY_PENDING, not a fabricated successful morph.
"""
from __future__ import annotations

import hashlib
import math
import os
import shutil
import time
from dataclasses import dataclass
from typing import Callable, FrozenSet, Mapping, Optional

from .continuity_admission import (
    HeartbeatRegistry, LeaseStore, LifeSignal, MorphBudget, MorphVerdict,
    Refused, Requirement, assess_morph_risk, prepare_preemptive_morph,
)

REQUIRED_CONTEXT_KEYS = frozenset((
    "schema", "mission_id", "source_sha", "resume_cursor",
    "instruction_id", "workflow_id", "plan_sha256", "bdd_ref",
    "estate_view_digest", "estate_view_observed_at", "next_action",
    "verified_effect_refs", "unresolved_effect_ids",
))
MANDATORY_LIFE_DOMAINS = frozenset((
    "context", "provider_quota", "host_memory", "storage", "network", "lease",
))
SHA256_LEN = 64


def _nonempty(v: object) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _digest(v: object) -> bool:
    return isinstance(v, str) and len(v) == SHA256_LEN and all(
        c in "0123456789abcdef" for c in v
    )


def _clock(v: object) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def _verified_checkpoint_manifest(mission_id: str, data: Mapping) -> dict:
    """Reject a checkpoint incapable of preserving mission/knowledge continuity.

    Only source refs/digests and action IDs; never copy credentials into memory.
    The OCI adapter itself enforces encrypted object storage, key binding and
    cryptographic integrity; this only strengthens semantic completeness.
    """
    if not isinstance(data, Mapping) or REQUIRED_CONTEXT_KEYS - set(data):
        raise Refused("MORPH_CHECKPOINT_INCOMPLETE")
    if (data.get("schema") != "genesis.mission.checkpoint.v1"
            or data.get("mission_id") != mission_id
            or not isinstance(data.get("source_sha"), str)
            or len(data["source_sha"]) != 40
            or any(c not in "0123456789abcdef" for c in data["source_sha"])
            or not _nonempty(data.get("resume_cursor"))
            or not _nonempty(data.get("instruction_id"))
            or not _nonempty(data.get("workflow_id"))
            or not _nonempty(data.get("bdd_ref"))
            or not _nonempty(data.get("next_action"))
            or not _digest(data.get("plan_sha256"))
            or not _digest(data.get("estate_view_digest"))
            or not _clock(data.get("estate_view_observed_at"))
            or type(data.get("verified_effect_refs")) is not list
            or type(data.get("unresolved_effect_ids")) is not list
            or not all(_nonempty(item) for item in
                       data["verified_effect_refs"] + data["unresolved_effect_ids"])):
        raise Refused("MORPH_CHECKPOINT_INVALID")
    if (data.get("authorized") or data.get("operating")
            or any(k in data for k in ("password", "access_token", "api_key",
                                      "private_key", "credential_value"))):
        raise Refused("MORPH_CHECKPOINT_FORBIDDEN_AUTHORITY")
    if data["unresolved_effect_ids"]:
        raise Refused("MORPH_EFFECTS_REQUIRE_RECONCILIATION")
    return dict(data)


@dataclass(frozen=True)
class Observation:
    """Source-pinned telemetry gathered by a trusted adapter, not from model text."""
    resource: str
    remaining: Optional[float]
    burn_per_second: Optional[float]
    deadline: Optional[float]
    observed_at: float
    source: str
    evidence: str
    failed: bool = False

    def to_life_signal(self) -> LifeSignal:
        return LifeSignal(self.resource, self.observed_at, self.source,
                          self.evidence, self.remaining,
                          self.burn_per_second, self.deadline, self.failed)


class BrokerLifeObserver:
    """Resource sampling for the machine this broker actually inhabits.

    Host measurements NEVER substitute for remote Pi/cloud model telemetry.
    Context, provider quota and network are UNKNOWN unless a trusted adapter
    supplies fresh authenticated observations.
    """

    def __init__(self, *, required: FrozenSet[str] = MANDATORY_LIFE_DOMAINS):
        if not isinstance(required, frozenset) or not required:
            raise Refused("MORPH_RESOURCE_POLICY_REQUIRED")
        self.required = required

    def sample_storage(self, path: str, *, now: float) -> Observation:
        if not _clock(now) or not isinstance(path, str) or not path:
            raise Refused("INVALID_STORAGE_OBSERVATION")
        # Reliable disk free space, NOT a fabricated depletion rate.
        try:
            free = shutil.disk_usage(path).free
        except (OSError, ValueError):
            return Observation("storage", None, None, None, now,
                               "unknown", "unavailable:disk_usage")
        return Observation("storage", float(free), None, None, now,
                           "host_metrics", "kernel:disk_usage:" + os.path.realpath(path))

    def sample_lease(self, lease_store: LeaseStore, mission_id: str,
                     *, now: float) -> Observation:
        if not _clock(now):
            raise Refused("INVALID_BROKER_CLOCK")
        lease = lease_store.snapshot(mission_id)
        if lease is None:
            return Observation("lease", None, None, None, now,
                               "unknown", "unavailable:mission_lease")
        _, epoch, expires_at, _, _ = lease
        # The observer must run inside the trusted broker, not a remote agent.
        return Observation("lease", None, None, float(expires_at), now,
                           "trusted_supervisor", f"broker:lease:{mission_id}:{epoch}")

    def assess(self, observations: Mapping[str, Observation], *,
               now: float, budget: MorphBudget,
               checkpoint_age_seconds: Optional[float],
               previous_state: str = "UNKNOWN", clear_count: int = 0) -> MorphVerdict:
        if not isinstance(observations, Mapping):
            raise Refused("INVALID_MORPH_OBSERVATIONS")
        values = []
        for name, item in observations.items():
            if name != item.resource or name not in self.required:
                raise Refused("UNDECLARED_MORPH_OBSERVATION")
            values.append(item.to_life_signal())
        policy = MorphBudget(
            budget.checkpoint_seconds, budget.destination_seconds,
            budget.restore_verify_seconds, budget.safety_margin_seconds,
            budget.max_signal_age_seconds, budget.max_checkpoint_age_seconds,
            self.required,
        )
        return assess_morph_risk(
            values, now=now, budget=policy,
            checkpoint_age_seconds=checkpoint_age_seconds,
            previous_state=previous_state,
            consecutive_clear_observations=clear_count,
        )


def _pending(reason: str, *, mission_id: str, epoch: Optional[int] = None) -> dict:
    return {
        "state": "RECOVERY_PENDING", "mission_id": mission_id, "reason": reason,
        "lease_epoch": epoch, "operationally_complete": False,
        "runtime_dispatch_verified": False,
    }


class MorphCoordinator:
    """One bounded operation; existing Temporal worker owns retries/scheduling.

    All dependencies are constructed by the trusted server. Do not expose this
    constructor, caller arguments, signers or injected callbacks to a model,
    browser or untrusted adapter.
    """

    def __init__(
        self, *, leases: LeaseStore, beats: HeartbeatRegistry,
        checkpoint_store: object,
        authorize_and_sign: Callable[[Mapping], bytes],
        durable_event: Callable[[Mapping], str],
        dispatch_existing_workflow: Callable[[Mapping], str],
    ):
        self.leases = leases
        self.beats = beats
        self.checkpoints = checkpoint_store
        self.authorize_and_sign = authorize_and_sign
        self.durable_event = durable_event
        self.dispatch = dispatch_existing_workflow

    def morph(
        self, *, mission_id: str, current_worker: str, epoch: int,
        observed_at: float, lease_ttl: float, progress_sequence: int,
        verdict: MorphVerdict, requirement: Requirement,
        context: Mapping,
    ) -> dict:
        """Checkpoint -> verify -> signed CAS -> dispatch. Never assert yield."""
        if (not _nonempty(mission_id) or not _nonempty(current_worker)
                or type(epoch) is not int or epoch < 1
                or type(progress_sequence) is not int or progress_sequence < 1
                or not _clock(observed_at) or not _clock(lease_ttl)
                or lease_ttl <= 0 or not isinstance(verdict, MorphVerdict)):
            raise Refused("INVALID_MORPH_REQUEST")
        if verdict.state not in ("AT_RISK", "CRITICAL"):
            return {"state": "NOT_TRIGGERED", "risk": verdict.state,
                    "mission_id": mission_id, "operationally_complete": False}
        if not all(callable(f) for f in (
                self.authorize_and_sign, self.durable_event, self.dispatch)):
            return _pending("TRUSTED_INTEGRATION_UNAVAILABLE", mission_id=mission_id)
        if not all(callable(getattr(self.checkpoints, name, None)) for name in (
                "write", "read_ciphertext", "decrypt_and_validate")):
            return _pending("ENCRYPTED_OFFHOST_CHECKPOINT_UNAVAILABLE", mission_id=mission_id)
        try:
            manifest = _verified_checkpoint_manifest(mission_id, context)
        except Refused as exc:
            return _pending(str(exc), mission_id=mission_id)
        old = self.leases.snapshot(mission_id)
        if old is None or old[0] != current_worker or old[1] != epoch:
            return _pending("CURRENT_MISSION_OWNER_NOT_VERIFIED", mission_id=mission_id)
        if observed_at >= old[2]:
            return _pending("LEASE_EXPIRED_USE_RECOVERY", mission_id=mission_id)
        try:
            ref = self.checkpoints.write(mission_id, manifest)
            # Write/readback is part of store.write; still authenticate by
            # decrypting the exact object to check identity and source.
            data = self.checkpoints.read_ciphertext(ref.uri)
            if hashlib.sha256(data).hexdigest() != ref.sha256:
                raise Refused("CHECKPOINT_READBACK_MISMATCH")
            recovered = self.checkpoints.decrypt_and_validate(mission_id, ref.uri, data)
            _verified_checkpoint_manifest(mission_id, recovered)
            if recovered != manifest:
                raise Refused("CHECKPOINT_SEMANTIC_MISMATCH")
            # Link the checkpoint to existing lease/custody, and only then
            # select an alternate execution destination.
            self.leases.heartbeat(
                mission_id, current_worker, epoch,
                observed_at, lease_ttl, progress_sequence,
                ref.sha256, ref.uri,
            )
            proposal = prepare_preemptive_morph(
                mission_id, self.leases, self.beats, requirement,
                verdict, observed_at, self.checkpoints.read_ciphertext,
                self.checkpoints.decrypt_and_validate,
            )
        except Exception as exc:
            return _pending(
                str(exc) if isinstance(exc, Refused) else
                "CHECKPOINT_OR_PREPARATION_FAILED",
                mission_id=mission_id,
            )
        if proposal.get("state") != "READY_FOR_SIGNED_HANDOVER":
            return _pending(proposal.get("reason", "MORPH_NOT_READY"),
                            mission_id=mission_id)
        proposal = dict(proposal)
        proposal.update({
            "now": observed_at, "lease_ttl": lease_ttl,
            "authority_requested": True, "operationally_complete": False,
        })
        # Durable intent-before-effect. The recorded proposal is a request,
        # not an authorization or a completed outcome.
        try:
            before = self.durable_event({
                "kind": "MORPH_PREPARED", "mission_id": mission_id,
                "old_epoch": epoch, "source_sha": manifest["source_sha"],
                "checkpoint_sha256": ref.sha256,
                "new_worker": proposal["new_worker"],
            })
            if not _nonempty(before):
                raise Refused("DURABLE_EVENT_NOT_ACKNOWLEDGED")
            proof = self.authorize_and_sign(proposal)
            if type(proof) is not bytes or not proof:
                raise Refused("INDEPENDENT_AUTHORIZATION_MISSING")
        except Exception as exc:
            return _pending(
                str(exc) if isinstance(exc, Refused) else
                "TRUSTED_AUTHORIZATION_UNAVAILABLE",
                mission_id=mission_id,
            )
        # The action door MUST re-evaluate current DoF, identity and capacity
        # immediately before signing; caller arguments can never grant access.
        try:
            new_epoch = self.leases.preemptive_handover(
                mission_id, current_worker, epoch, proposal["new_worker"],
                observed_at, lease_ttl, ref.sha256, ref.uri,
                handover_proof=proof,
            )
        except Refused as exc:
            return _pending(str(exc), mission_id=mission_id)
        result = {
            "state": "CUSTODY_TRANSFERRED",
            "mission_id": mission_id, "old_worker": current_worker,
            "new_worker": proposal["new_worker"], "lease_epoch": new_epoch,
            "checkpoint_sha256": ref.sha256, "checkpoint_uri": ref.uri,
            "source_sha": manifest["source_sha"], "resume_cursor": manifest["resume_cursor"],
            "operationally_complete": False, "runtime_dispatch_verified": False,
            "reconcile_current_oracle_and_dof": True,
        }
        # This is a custody proof, not a dispatch/completion proof. Failure
        # cannot roll back the epoch: old agent must remain fenced.
        try:
            receipt = self.durable_event({
                "kind": "MORPH_CUSTODY_TRANSFERRED", **result,
            })
            if not _nonempty(receipt):
                raise Refused("CUSTODY_EVENT_NOT_ACKNOWLEDGED")
            dispatch_receipt = self.dispatch(dict(result))
            if not _nonempty(dispatch_receipt):
                raise Refused("WORKFLOW_DISPATCH_NOT_ACKNOWLEDGED")
        except Exception:
            return _pending("FENCED_OWNER_PENDING_WORKFLOW_RECOVERY",
                            mission_id=mission_id, epoch=new_epoch)
        result["state"] = "DISPATCH_ACKNOWLEDGED_NOT_VERIFIED"
        result["dispatch_receipt"] = dispatch_receipt
        # Never promote to OPERATIONAL without independent new-worker effect.
        return result

"""Strict record fields and exceptions for mission custody (ESTATE-P0)."""

from __future__ import annotations


class RecordRejected(Exception):
    """A record failed strict validation."""


class UnknownField(RecordRejected):
    """The record carries a field outside the declared schema."""


class InvalidTransition(RecordRejected):
    """The requested state transition is not in the canonical machine."""


class LeaseNotAcquired(RecordRejected):
    """Another worker holds the lease for this epoch window."""


class StaleFenceError(RecordRejected):
    """The (attempt_id, lease_epoch) pair is not the current owner."""


class FencedWriteError(RecordRejected):
    """A mediated write was refused by the fence check."""


class DuplicateEffect(RecordRejected):
    """An external effect with this idempotency key already exists."""


class CheckpointRejected(RecordRejected):
    """A checkpoint failed reconstruction validation."""


MISSION_FIELDS = (
    "mission_id",
    "parent_mission_id",
    "instruction_id",
    "mandate_id",
    "mandate_version",
    "revocation_epoch",
    "goal",
    "acceptance_contract_digest",
    "risk_class",
    "priority",
    "dependencies",
    "state",
    "authoritative_owner",
    "created_at",
    "deadline",
    "retry_budget",
    "retry_budget_remaining",
    "cost_budget",
    "recovery_policy",
    "current_attempt_id",
    "current_lease_epoch",
    "last_verified_progress_at",
    "last_checkpoint_digest",
    "last_observed_outcome",
)

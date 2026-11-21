"""Record shapes, states and transitions for mission custody (ESTATE-P0)."""

from __future__ import annotations

from typing import Dict

CHECKPOINT_SCHEMA_VERSION = 1
NO_PROGRESS_BOUND_S = 600.0

MISSION_STATES = (
    "ACCEPTED",
    "READY",
    "LEASED",
    "EXECUTING",
    "CHECKPOINTING",
    "RECOVERY_PENDING",
    "REASSIGNING",
    "VERIFYING",
    "PROMOTING",
    "DEPLOY_VERIFY",
    "OPERATING",
    "YIELD_PROVEN",
    "SETTLED",
)

TRANSITIONS: Dict[str, frozenset] = {
    "ACCEPTED": frozenset({"READY"}),
    "READY": frozenset({"LEASED"}),
    "LEASED": frozenset({"EXECUTING", "RECOVERY_PENDING"}),
    "EXECUTING": frozenset({"CHECKPOINTING", "RECOVERY_PENDING", "VERIFYING"}),
    "CHECKPOINTING": frozenset({"EXECUTING"}),
    "RECOVERY_PENDING": frozenset({"REASSIGNING"}),
    "REASSIGNING": frozenset({"LEASED"}),
    "VERIFYING": frozenset({"PROMOTING", "RECOVERY_PENDING"}),
    "PROMOTING": frozenset({"DEPLOY_VERIFY", "RECOVERY_PENDING"}),
    "DEPLOY_VERIFY": frozenset({"OPERATING", "RECOVERY_PENDING"}),
    "OPERATING": frozenset({"YIELD_PROVEN"}),
    "YIELD_PROVEN": frozenset({"SETTLED"}),
    "SETTLED": frozenset(),
}

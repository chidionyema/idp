"""Read-only root-directed control decisions using existing mission custody.

The result is advisory, never a lease, command, or authorization. Execution
must still pass the existing authority, fence and independent proof doors.
"""

from __future__ import annotations

from .fields import InvalidTransition

ACTIVE = frozenset(
    {"LEASED", "EXECUTING", "CHECKPOINTING", "VERIFYING", "PROMOTING", "DEPLOY_VERIFY"}
)


class ControlMixin:
    def control_step(self, mission_id: str, *, now: float | None = None) -> dict:
        """Unwind settled detours and return to the conserved root obligation.

        Parent links are custody, not evidence of completed prerequisites.
        Only explicit dependencies can redirect the root to required work.
        Read a coherent SQLite snapshot; never mutate authority or budgets.
        """
        self.db.execute("BEGIN")
        try:
            return self._control_step(mission_id, now)
        finally:
            self.db.execute("ROLLBACK")

    def _control_step(self, mission_id, now):
        current = self._require(mission_id)
        seen = {mission_id}
        while current["parent_mission_id"] is not None:
            parent = current["parent_mission_id"]
            if parent in seen:
                raise InvalidTransition("cyclic objective ancestry")
            seen.add(parent)
            current = self._require(parent)
        root = current
        path = set()

        def decision(mission):
            identity = mission["mission_id"]
            if identity in path:
                raise InvalidTransition("cyclic objective dependencies")
            path.add(identity)
            if mission["state"] == "OPERATING":
                path.remove(identity)
                return None
            if mission["revocation_epoch"] != 0:
                return identity, "RECONCILE_AUTHORITY"
            dependencies = mission["dependencies"]
            if not isinstance(dependencies, list) or any(
                not isinstance(dep, str) or not dep for dep in dependencies
            ):
                raise InvalidTransition("invalid mission dependencies")
            for dep in dependencies:
                required = self._require(dep)
                result = decision(required)
                if result is not None:
                    return result
            state = mission["state"]
            if state in ACTIVE:
                action = (
                    "RECOVER"
                    if self.needs_takeover(identity, now=now)["takeover"]
                    else "CONTINUE"
                )
            elif state in ("RECOVERY_PENDING", "REASSIGNING"):
                action = (
                    "RESELECT"
                    if mission["retry_budget_remaining"] > 0
                    else "RECONCILE_CAPACITY"
                )
            elif state == "ACCEPTED":
                action = "ADMIT"
            elif state == "READY":
                action = "CLAIM"
            else:
                raise InvalidTransition("unknown mission state")
            return identity, action

        target = decision(root)
        return {
            "root_mission_id": root["mission_id"],
            "instruction_id": root["instruction_id"],
            "goal": root["goal"],
            "acceptance_contract_digest": root["acceptance_contract_digest"],
            "target_mission_id": target[0] if target else root["mission_id"],
            "action": target[1] if target else "VERIFY_EXISTING_OPERATING",
        }

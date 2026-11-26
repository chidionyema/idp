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
        while True:
            identity = current["mission_id"]
            if identity in path:
                raise InvalidTransition("cyclic objective dependencies")
            path.add(identity)
            state = current["state"]
            if current["revocation_epoch"] != 0:
                action = "RECONCILE_AUTHORITY"
                break
            if state == "OPERATING":
                action = "VERIFY_EXISTING_OPERATING"
                break
            dependencies = current["dependencies"]
            if not isinstance(dependencies, list) or any(
                not isinstance(dep, str) or not dep for dep in dependencies
            ):
                raise InvalidTransition("invalid mission dependencies")
            for dep in dependencies:
                required = self._require(dep)
                if (
                    required["state"] != "OPERATING"
                    or required["revocation_epoch"] != 0
                ):
                    current = required
                    break
            else:
                if state in ACTIVE:
                    action = (
                        "RECOVER"
                        if self.needs_takeover(identity, now=now)["takeover"]
                        else "CONTINUE"
                    )
                elif state in ("RECOVERY_PENDING", "REASSIGNING"):
                    action = (
                        "RESELECT"
                        if current["retry_budget_remaining"] > 0
                        else "RECONCILE_CAPACITY"
                    )
                elif state == "ACCEPTED":
                    action = "ADMIT"
                elif state == "READY":
                    action = "CLAIM"
                else:
                    raise InvalidTransition("unknown mission state")
                break

        return {
            "root_mission_id": root["mission_id"],
            "instruction_id": root["instruction_id"],
            "goal": root["goal"],
            "acceptance_contract_digest": root["acceptance_contract_digest"],
            "target_mission_id": identity,
            "action": action,
        }

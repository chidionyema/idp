"""Paid-compute activation gate (idp#3525 CP1, COST-02).

"Any action that provisions paid compute (tier activation, GPU rental,
cluster resize) SHALL require a hardware-rooted signature ... in addition
to budget check. No signature path -> the action is architecturally
impossible, not just policy-blocked."

This module is the one place a provisioning callable may be invoked from.
It reuses the same envelope/verify/spend contract cp29 built for `sb
approve` (sovereign/trust/approval.py) rather than inventing a second
signature scheme -- a paid-compute activation and a rewind are refused by
identical machinery, so a defect found in one path is a defect found in
both.

"Architecturally impossible" is enforced by control flow, not a flag:
`activate()` never has a code path that reaches `provision(...)` before
`approval.verify()` has already returned `ok: True`. There is no
`if require_signature:` to leave off.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sovereign.engine import ops
from sovereign.trust import approval

PROVISION_ACTION = "provision_paid_compute"


class MisconfiguredOp(RuntimeError):
    """PROVISION_ACTION is not classified destructive. This must never be
    reachable in a correctly configured estate (AGENTS.md's capabilities
    block lists it under `destructive`); it exists so a future edit that
    silently reclassifies the op fails loudly instead of quietly
    dropping the hardware-signature requirement."""


@dataclass(frozen=True)
class ActivationResult:
    ok: bool
    reason: str | None
    attestation: str | None
    counter: int | None
    tier: str
    provisioned: bool


def activate(
    tier: str,
    envelope: dict[str, Any] | None,
    provision: Callable[[str], Any],
) -> ActivationResult:
    """Attempt to activate a paid compute tier.

    `provision` is called at most once, only on the single path where a
    signed approval verifies. Every refusal path returns before
    `provision` is referenced at all -- per COST-02's ACCEPT line, an
    unsigned attempt makes "no provisioning call."
    """
    spec = ops.classify(PROVISION_ACTION)
    if not spec.destructive:
        raise MisconfiguredOp(
            f"{PROVISION_ACTION!r} classified {spec.classification!r}, expected destructive "
            "(check AGENTS.md capabilities.destructive)"
        )

    verdict = approval.verify(envelope)
    if not verdict["ok"]:
        return ActivationResult(
            False, verdict["reason"], None, None, tier, provisioned=False
        )

    # Spend the counter before acting: a crash between the two must leave
    # an approval that cannot be replayed, not one that can (same
    # ordering as cmd_approve in sovereign/cli.py).
    approval.spend(int(verdict["counter"]))
    provision(tier)
    return ActivationResult(
        True,
        None,
        verdict["attestation"],
        int(verdict["counter"]),
        tier,
        provisioned=True,
    )

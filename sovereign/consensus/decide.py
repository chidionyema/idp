"""One decision: do the models agree, and does policy allow it anyway
(cp30, spec v1.0 4.2).

The ordering here is the requirement, not an implementation detail.
Consensus is computed first and policy second, and policy can only ever
turn a yes into a no -- it is never consulted to rescue a failed quorum.
That is what "policy is a hard safety invariant above consensus" means,
and the receipt says which of the two refused so the founder never has to
guess whether three models disagreed or all three were wrong together.

Every outcome is a receipt (cp19's signed chain, kind "model_consensus"),
including the refusals. A blocked destructive op that leaves no trace is
the same as no guard at all the next time somebody asks what happened.
"""
from __future__ import annotations

import asyncio
from typing import Any

from sovereign.consensus import models as models_mod
from sovereign.consensus import policy as policy_mod

REASON_POLICY = "policy"
REASON_QUORUM = "quorum"
REASON_STALE = "stale"


def _receipt(payload: dict[str, Any]) -> None:
    from sovereign.engine import receipts as receipts_mod

    receipts_mod.append(payload)


async def decide_async(
    op: str,
    destructive: bool | None = None,
    deadline_s: float | None = None,
    write_receipt: bool = True,
) -> dict[str, Any]:
    """Returns {"ok", "reason", "proposal", "votes", "quorum", "policy",
    "destructive"}."""
    destructive = models_mod.is_destructive(op) if destructive is None else bool(destructive)
    votes = await models_mod.collect(op, destructive, deadline_s)
    quorum = models_mod.tally(votes)

    if not destructive:
        # spec 4.2: a non-destructive op is one cheap model's answer. There
        # is no quorum to meet, so `agreed` is not the gate -- the single
        # fresh answer is. Policy still runs: one model's proposal is not
        # a licence either.
        fresh = [v for v in votes if not v.get("stale") and not v.get("error") and v.get("proposal")]
        proposal = str(fresh[0]["proposal"]) if fresh else ""
    else:
        proposal = str(quorum["proposal"])

    if not proposal:
        reason = REASON_STALE if quorum["stale"] else REASON_QUORUM
        result = {
            "ok": False, "reason": reason, "proposal": "", "votes": votes,
            "quorum": quorum, "policy": None, "destructive": destructive,
        }
        if write_receipt:
            _receipt(_as_receipt(op, result))
        return result

    verdict = policy_mod.evaluate(proposal, destructive)
    ok = bool(verdict["allowed"])
    result = {
        "ok": ok,
        "reason": None if ok else REASON_POLICY,
        "proposal": proposal,
        "votes": votes,
        "quorum": quorum,
        "policy": verdict,
        "destructive": destructive,
    }
    if write_receipt:
        _receipt(_as_receipt(op, result))
    return result


def _as_receipt(op: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "session_id": "-",
        "kind": "model_consensus",
        "by": "engine",
        "text": op,
        "step": 0,
        "status": "allowed" if result["ok"] else "blocked",
        "task": op,
        "runner": "consensus",
        "reason": result["reason"],
        "proposal": result["proposal"],
        "destructive": result["destructive"],
        # The three votes by name, so the receipt "names the three votes"
        # cp30 asks for rather than just their count.
        "votes": [
            {"model": v.get("model"), "proposal": v.get("proposal"),
             "stale": bool(v.get("stale")), "error": v.get("error")}
            for v in result["votes"]
        ],
        "quorum": result["quorum"],
        "policy_violations": (result["policy"] or {}).get("violations", []),
    }


def decide(
    op: str,
    destructive: bool | None = None,
    deadline_s: float | None = None,
    write_receipt: bool = True,
) -> dict[str, Any]:
    """Blocking wrapper for the CLI."""
    return asyncio.run(decide_async(op, destructive, deadline_s, write_receipt))

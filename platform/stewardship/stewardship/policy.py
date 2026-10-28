"""Explicit delegated authority; research never implies production authorization."""

from dataclasses import dataclass
from .core import Refused


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
    required_gate: str


def authorize(change: dict, policy: dict) -> Decision:
    required = (
        "risk",
        "reversible",
        "blast_radius",
        "estimated_cost",
        "claim_valid",
        "independent_verification",
        "mode",
    )
    missing = [k for k in required if k not in change]
    if missing:
        raise Refused("missing change fields: " + ",".join(missing))
    if change["mode"] in ("research", "specify", "benchmark"):
        return Decision(True, "non-mutating investigation", "evidence-record")
    if change["mode"] != "execute":
        raise Refused("unknown mode")
    if not change["claim_valid"]:
        return Decision(False, "estate claim not validated", "claim-gate")
    if not change["independent_verification"]:
        return Decision(False, "independent verification missing", "verification-gate")
    if change["risk"] not in ("low", "medium", "high") or change[
        "blast_radius"
    ] not in ("isolated", "shared", "estate"):
        raise Refused("unknown risk or blast radius")
    if (
        not isinstance(change["estimated_cost"], (int, float))
        or change["estimated_cost"] < 0
    ):
        raise Refused("invalid estimated cost")
    if (
        not change["reversible"]
        or change["risk"] == "high"
        or change["blast_radius"] == "estate"
    ):
        return Decision(
            False, "outside delegated change authority", "founder-or-policy-gate"
        )
    if change.get("new_infrastructure") or change.get("changes_security_boundary"):
        return Decision(
            False,
            "requires architecture and security authorization",
            "architecture-gate",
        )
    if change["estimated_cost"] > policy.get("max_autonomous_cost", 0):
        return Decision(False, "exceeds delegated cost ceiling", "budget-gate")
    if change["risk"] == "medium" or change["blast_radius"] == "shared":
        if not policy.get("allow_shared_changes", False):
            return Decision(
                False, "shared change not delegated", "independent-approval"
            )
    if not change.get("baseline_evidence") or not change.get("rollback_plan"):
        return Decision(False, "baseline or rollback missing", "experiment-gate")
    return Decision(
        True, "within explicit delegated authority", "existing-estate-gates"
    )


def compare(before: list, after: list, quality_floor=1.0):
    if not before or not after or len(before) != len(after):
        raise Refused("paired nonempty measurements required")
    for group in (before, after):
        if any(
            not isinstance(x, dict)
            or any(k not in x for k in ("success", "latency_ms", "cost"))
            for x in group
        ):
            raise Refused("missing measurement")

    def metric(group):
        return {
            "success_rate": sum(bool(x["success"]) for x in group) / len(group),
            "mean_latency_ms": sum(x["latency_ms"] for x in group) / len(group),
            "mean_cost": sum(x["cost"] for x in group) / len(group),
        }

    a, b = metric(before), metric(after)
    return {
        "baseline": a,
        "treatment": b,
        "accepted": b["success_rate"] >= a["success_rate"] * quality_floor,
        "warning": "Descriptive paired comparison only; not a statistical significance claim",
    }

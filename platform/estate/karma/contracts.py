"""KARMA instruction obligation projection over existing QUAD/FLOW event receipts.

Pure reducer; no independent event store or executor. Caller supplies a real
external verifier. Without it, no acceptance, payment, reward or yield may
become authoritative. Idempotent IDs, causal parents, explicit unknowns.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

KINDS = frozenset(
    {
        "INSTRUCTION_ACCEPTED",
        "OWNERSHIP_HANDBACK",
        "COST_OBSERVED",
        "YIELD_SUBMITTED",
        "YIELD_INDEPENDENTLY_VERIFIED",
        "ANCESTRAL_FAILURE",
        "CORRECTION_VERIFIED",
        "OBLIGATION_WITHDRAWN",
    }
)


def utc(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(dt.timezone.utc)


def project(events, verify_external=None):
    """A chronological *record* projection, not fictional causal inference.

    verify_external(event) must be supplied by the existing authorized QUAD /
    independent verification door. Caller-supplied boolean fields are ignored.
    """
    if not isinstance(events, list):
        raise ValueError("KARMA requires ordered durable event records")
    obligations = {}
    seen = set()
    gaps = []
    events_by_id = {}
    tallies = Counter()
    for number, e in enumerate(events):
        if (
            not isinstance(e, dict)
            or not isinstance(e.get("event_id"), str)
            or not e["event_id"]
        ):
            gaps.append({"index": number, "reason": "INVALID_EVENT_ID"})
            continue
        eid = e["event_id"]
        if eid in seen:
            gaps.append({"event": eid, "reason": "DUPLICATE_EVENT"})
            continue
        seen.add(eid)
        kind = e.get("kind")
        if kind not in KINDS:
            gaps.append({"event": eid, "reason": "UNKNOWN_EVENT_KIND"})
            continue
        when = utc(e.get("recorded_at"))
        if when is None:
            gaps.append({"event": eid, "reason": "RECORD_TIME_UNTRUSTED"})
            continue
        parents = e.get("parent_event_ids")
        if not isinstance(parents, list) or any(
            not isinstance(p, str) for p in parents
        ):
            gaps.append({"event": eid, "reason": "CAUSAL_PARENTS_UNDECLARED"})
            continue
        if any(p not in events_by_id for p in parents):
            gaps.append({"event": eid, "reason": "CAUSAL_PARENT_NOT_YET_OBSERVED"})
            continue
        oid = e.get("instruction_id")
        if not isinstance(oid, str) or not oid.strip():
            gaps.append({"event": eid, "reason": "UNLINKED_TO_INSTRUCTION"})
            continue
        actor = e.get("agent_urn") or "UNKNOWN"
        revision = e.get("model_revision") or "UNKNOWN"
        # A source's self-declared attestation is data. Only the external
        # verifier can authenticate the QUAD action and independent oracle.
        authenticated = False
        if verify_external is not None:
            try:
                authenticated = verify_external(e) is True
            except Exception:
                authenticated = False
        if not authenticated:
            gaps.append({"event": eid, "reason": "UNVERIFIED_EXTERNAL_AUTHORITY"})
            continue
        current = obligations.get(oid)
        if kind == "INSTRUCTION_ACCEPTED":
            if current is not None:
                gaps.append({"event": eid, "reason": "DUPLICATE_ACCEPTANCE"})
                continue
            if actor == "UNKNOWN" or not e.get("expected_outcome_digest"):
                gaps.append({"event": eid, "reason": "UNATTRIBUTABLE_OBLIGATION"})
                continue
            obligations[oid] = {
                "instruction_id": oid,
                "initial_agent": actor,
                "current_agent": actor,
                "provider": e.get("provider") or "UNKNOWN",
                "model_revision": revision,
                "generation": e.get("generation") or "UNKNOWN",
                "accepted_at": e["recorded_at"],
                "accepted_event": eid,
                "latest_event": eid,
                "expected_outcome_digest": e["expected_outcome_digest"],
                "state": "OPEN",
                "costs": {"tokens_in": 0, "tokens_out": 0},
                "cost_known": True,
                "money_cost": None,
                "yield_evidence": None,
                "verified_yield": False,
                "failures_inherited": [],
                "verified_corrections": [],
                "events": [eid],
            }
            events_by_id[eid] = e
            tallies[kind] += 1
            continue
        if current is None:
            gaps.append({"event": eid, "reason": "ACCEPTANCE_NOT_OBSERVED"})
            continue
        if current["latest_event"] not in parents:
            gaps.append({"event": eid, "reason": "BROKEN_OBLIGATION_CAUSAL_CHAIN"})
            continue
        if kind == "OWNERSHIP_HANDBACK":
            successor = e.get("successor_agent_urn")
            if not successor or successor == actor or actor != current["current_agent"]:
                gaps.append({"event": eid, "reason": "INVALID_HANDOVER_CUSTODY"})
                continue
            current["current_agent"] = successor
        elif kind == "COST_OBSERVED":
            inc = e.get("tokens_in")
            out = e.get("tokens_out")
            if (
                not isinstance(inc, int)
                or isinstance(inc, bool)
                or inc < 0
                or not isinstance(out, int)
                or isinstance(out, bool)
                or out < 0
            ):
                gaps.append({"event": eid, "reason": "INVALID_RESOURCE_COUNT"})
                continue
            current["costs"]["tokens_in"] += inc
            current["costs"]["tokens_out"] += out
            # Token quantity never determines billed cost without price source.
            if e.get("billing_verified") is True:
                gaps.append(
                    {
                        "event": eid,
                        "reason": "BILLING_ASSERTION_REQUIRES_SEPARATE_PRICING_AUTHORITY",
                    }
                )
            current["money_cost"] = None
        elif kind == "YIELD_SUBMITTED":
            current["yield_evidence"] = e.get("evidence_digest") or None
            current["state"] = "AWAITING_INDEPENDENT_YIELD"
        elif kind == "YIELD_INDEPENDENTLY_VERIFIED":
            if (
                actor == current["current_agent"]
                or not e.get("evidence_digest")
                or e["evidence_digest"] != current["yield_evidence"]
            ):
                gaps.append({"event": eid, "reason": "SELF_GRADED_OR_UNLINKED_YIELD"})
                continue
            current["verified_yield"] = True
            current["state"] = "SETTLED_VERIFIED"
        elif kind == "ANCESTRAL_FAILURE":
            if not e.get("failure_class") or not e.get("ancestor_event_id"):
                gaps.append({"event": eid, "reason": "UNATTRIBUTABLE_ANCESTOR_ERROR"})
                continue
            current["failures_inherited"].append(
                {
                    "failure_class": e["failure_class"],
                    "ancestor_event_id": e["ancestor_event_id"],
                    "outstanding": True,
                }
            )
        elif kind == "CORRECTION_VERIFIED":
            ancestor = e.get("ancestor_event_id")
            if (
                not ancestor
                or actor == current["current_agent"]
                or not e.get("falsifier_digest")
            ):
                gaps.append(
                    {"event": eid, "reason": "CORRECTION_NOT_INDEPENDENTLY_PROVEN"}
                )
                continue
            debt = next(
                (
                    x
                    for x in current["failures_inherited"]
                    if x["ancestor_event_id"] == ancestor and x["outstanding"]
                ),
                None,
            )
            if debt is None:
                gaps.append(
                    {"event": eid, "reason": "NO_OUTSTANDING_ANCESTRAL_FAILURE"}
                )
                continue
            debt["outstanding"] = False
            current["verified_corrections"].append(eid)
        elif kind == "OBLIGATION_WITHDRAWN":
            if actor == current["current_agent"] or not e.get("reason"):
                gaps.append(
                    {"event": eid, "reason": "WITHDRAWAL_REQUIRES_SEPARATE_AUTHORITY"}
                )
                continue
            current["state"] = "WITHDRAWN_WITH_REASON"
        current["latest_event"] = eid
        current["events"].append(eid)
        events_by_id[eid] = e
        tallies[kind] += 1
    return {
        "schema": "karma.obligation-projection.v1",
        "authority": "DERIVED_FROM_EXTERNALLY_VERIFIED_QUAD_FLOW_RECEIPTS",
        "operational_effect": "READ_ONLY_NOT_AN_EXECUTOR",
        "obligations": obligations,
        "unresolved": [
            oid
            for oid, o in obligations.items()
            if o["state"] not in ("SETTLED_VERIFIED", "WITHDRAWN_WITH_REASON")
        ],
        "outstanding_ancestor_failures": sum(
            sum(1 for f in o["failures_inherited"] if f["outstanding"])
            for o in obligations.values()
        ),
        "counts_by_event": dict(sorted(tallies.items())),
        "gaps": gaps,
    }

"""The lane in three answers, from the `idp-greenlane status` JSON and nothing else.

What is landing and for how long; what is stuck and why; what is red and who owns it. Pure: the
status payload in, a small dict out, so the Fleet dot, the Fleet detail and the spoken answer all
say the same thing because they are the same dict. Times are the engine's own clock (minutes), and
`now_min` rides in the payload so a reader never compares the engine's clock with its own.

`loud` is the one bit the Fleet dot obeys: the dot is quiet unless something needs a person.
"""

from __future__ import annotations

from typing import Any

LONG_TESTING_MIN = (
    30  # a batch under test longer than this is worth a look (p90 cycle is ~25)
)
GREEN = ("success", "skipped", "neutral")


def _mins(now: float | None, since: float | None) -> int | None:
    if not now or not since:
        return None
    return max(0, round(now - since))


def _owner(head: str, lane: dict, prs: list[dict]) -> str:
    if lane.get("owner"):
        return str(lane["owner"])
    for p in prs:
        if p.get("head") == head:
            return f"{p.get('user')} #{p.get('number')}"
    return "no open PR"


def brief(status: dict[str, Any]) -> dict[str, Any]:
    st = status.get("state") or {}
    lanes: dict[str, dict] = st.get("lanes") or {}
    prs = status.get("open_prs") or []
    now = status.get("now_min")

    batch = st.get("batch")
    landing = None
    if batch:
        landing = {
            "lanes": [m[0] for m in batch.get("members", [])],
            "minutes": _mins(now, batch.get("started")),
        }
    waiting = sum(1 for lane in lanes.values() if lane.get("status") == "pending")
    held_claims = [
        {"lane": name, "why": lane.get("reason") or "claim missing"}
        for name, lane in lanes.items()
        if lane.get("status") == "pending"
        and (lane.get("reason") or "")
        .lower()
        .startswith(("no live claim", "claim refused", "missing claim"))
    ]

    stuck = [
        {
            "lane": n,
            "why": lane.get("reason") or lane.get("status"),
            "status": lane.get("status"),
        }
        for n, lane in lanes.items()
        if lane.get("status") == "conflict"
    ]
    if (
        landing
        and landing["minutes"] is not None
        and landing["minutes"] > LONG_TESTING_MIN
    ):
        for n in landing["lanes"]:
            stuck.append(
                {
                    "lane": n,
                    "why": f"under test {landing['minutes']} min, past {LONG_TESTING_MIN}",
                    "status": "testing",
                }
            )

    red = [
        {"lane": n, "why": lane.get("reason") or "red", "owner": _owner(n, lane, prs)}
        for n, lane in lanes.items()
        if lane.get("status") == "red"
    ]
    for h in held_claims:
        stuck.append({"lane": h["lane"], "why": h["why"], "status": "claim-held"})
    common_blockers = [
        {"lane": entry["lane"], "reason": entry["why"]}
        for entry in red
        if entry["why"].startswith("trusted DoF [")
    ]
    # The record is a bounded 200-batch sample; it must not masquerade as a
    # production-wide or lifetime failure percentage.
    latency = st.get("latency") or {}
    outcomes = latency.get("outcomes") or {}
    sample = sum(v for v in outcomes.values() if isinstance(v, int) and v >= 0)
    landed_sample = outcomes.get("landed", 0)
    timeouts = sum(v for k, v in outcomes.items() if k.startswith("timeout"))
    bisected = sum(v for k, v in outcomes.items() if k.endswith("/bisected"))
    rate = round(100 * landed_sample / sample, 1) if sample else None
    batch_age = landing["minutes"] if landing else None
    max_queue_age = max(
        (
            _mins(now, lane.get("arrived"))
            for lane in lanes.values()
            if lane.get("status") in ("pending", "testing")
            and _mins(now, lane.get("arrived")) is not None
        ),
        default=None,
    )
    candidate_checks = status.get("candidate_checks") or {}
    blocking_checks = [
        {"name": k, **v}
        for k, v in candidate_checks.items()
        if isinstance(v, dict) and v.get("result") not in GREEN
    ]
    # Existing snapshot-only consumers omit "available"; production status
    # explicitly sets it false when state cannot be read.
    state_known = st.get("available") is not False
    visibility_blind = not state_known or any(
        str(c.get("result", "")).startswith("unreadable") for c in blocking_checks
    )
    service_state = (
        "UNKNOWN"
        if visibility_blind
        else "RED"
        if (status.get("alarm") or red or stuck)
        else "TESTING"
        if landing
        else "WAITING"
        if waiting
        else "IDLE"
    )

    required = (status.get("main") or {}).get("required") or {}
    main_red = [k for k, v in required.items() if v not in GREEN]
    lost = (status.get("invariants") or {}).get("work_lost") or 0
    loud = bool(
        not state_known
        or status.get("alarm")
        or main_red
        or lost
        or red
        or stuck
        or (batch_age is not None and batch_age >= 90)
        or any(
            str(b.get("result", "")).startswith("unreadable") for b in blocking_checks
        )
    )

    # Founder cockpit gets one executable next action and the evidence link
    # from the check-run response, rather than a generic red light.
    next_action = None
    if not state_known:
        next_action = {
            "code": "restore-state-read",
            "why": "Greenlane state unavailable",
        }
    elif main_red:
        next_action = {"code": "repair-required-main-check", "check": main_red[0]}
    elif blocking_checks and (
        batch_age is not None
        and batch_age >= LONG_TESTING_MIN
        or any(
            c.get("result") in ("failure", "timed_out", "cancelled")
            for c in blocking_checks
        )
        or visibility_blind
    ):
        target = blocking_checks[0]
        next_action = {
            "code": "inspect-candidate-check",
            "check": target["name"],
            "result": target["result"],
            "url": target.get("url"),
        }
    elif held_claims:
        next_action = {
            "code": "renew-claim",
            "lane": held_claims[0]["lane"],
            "why": held_claims[0]["why"],
        }
    elif common_blockers:
        next_action = {
            "code": "operations-reaction",
            "incident": "chidionyema/idp#7800",
            "issue_url": "https://github.com/chidionyema/idp/issues/7800",
            "blocked_lanes": [item["lane"] for item in common_blockers],
            "why": common_blockers[0]["reason"],
            "owner": "existing incident / R-14",
        }
    elif red:
        next_action = {
            "code": "repair-red-lane",
            "lane": red[0]["lane"],
            "owner": red[0]["owner"],
            "why": red[0]["why"],
        }
    elif stuck:
        next_action = {
            "code": "investigate-stuck-lane",
            "lane": stuck[0]["lane"],
            "why": stuck[0]["why"],
        }

    parts = []
    if landing and landing["lanes"]:
        n, m = len(landing["lanes"]), landing["minutes"]
        parts.append(
            f"{n} lane{'s' if n != 1 else ''} landing"
            + (f", testing {m} minute{'s' if m != 1 else ''}" if m is not None else "")
            + (f", {waiting} waiting" if waiting else "")
        )
    elif waiting:
        parts.append(f"nothing under test, {waiting} waiting")
    else:
        parts.append("nothing landing")
    if not state_known:
        parts.append("Greenlane state unreadable: no operational all-clear")
    if main_red:
        parts.append(f"main is red on {', '.join(main_red)}")
    if blocking_checks and landing:
        names = ", ".join(b["name"] for b in blocking_checks[:3])
        parts.append(f"candidate outstanding on {names}")
    if lost:
        parts.append(f"{lost} pull request{'s' if lost != 1 else ''} lost work")
    if stuck:
        s = stuck[0]
        parts.append(
            f"{len(stuck)} stuck, first {s['lane'].removeprefix('lane/')}: {s['why']}"
        )
    if red:
        r = red[0]
        parts.append(
            f"{len(red)} red, first {r['lane'].removeprefix('lane/')}, owner {r['owner']}"
        )
    if common_blockers:
        parts.append(
            f"{len(common_blockers)} affected by trusted DoF; "
            "Operations Reaction owns existing incident idp#7800"
        )
    if state_known and not (main_red or lost or stuck or red or blocking_checks):
        parts.append("all clear")

    return {
        "loud": loud,
        "landing": landing,
        "waiting": waiting,
        "stuck": stuck,
        "red": red,
        "main_red": main_red,
        "work_lost": lost,
        "assurance": {
            "state": service_state,
            "state_observed": state_known,
            "batch_age_min": batch_age,
            "batch_warning_after_min": LONG_TESTING_MIN,
            "batch_timeout_after_min": 90,
            "batch_overdue": batch_age is not None and batch_age >= 90,
            "pending_lanes": waiting,
            "oldest_pending_or_testing_age_min": max_queue_age,
            "held_claims": held_claims,
            "common_mode_refusals": {
                "count": len(common_blockers),
                "lanes": [x["lane"] for x in common_blockers],
                "canonical_incident": "chidionyema/idp#7800"
                if common_blockers
                else None,
                "owner": "operations-reaction" if common_blockers else None,
            },
            "candidate_blocking_checks": blocking_checks,
            "next_action": next_action,
            "batch_outcome_sample": {
                "n": sample,
                "landed": landed_sample,
                "timeouts": timeouts,
                "bisected": bisected,
                "landed_batch_pct": rate,
                "caveat": "last 200 recorded batches; not a lifetime promotion rate",
            },
            "queue_to_land_min": latency.get("queue_to_land_min") or {},
            "batch_cycle_min": latency.get("batch_cycle_min") or {},
            "cost_per_accepted_change_gbp": None,
            "cost_evidence": "UNKNOWN: no billable provider/runner receipt linked",
        },
        "summary": ". ".join(parts) + ".",
    }


def candidate_check_index(
    payload: dict | None, required: list[str], error: str = ""
) -> dict:
    """One bounded candidate check read, never inventing green on API failure.

    Workflows generate many optional check-runs. The first page suffices when
    total_count fits; if GitHub paginates, unobserved required contexts are
    UNKNOWN (not absent/pass) until an exact-name reader checks them.
    """
    if not isinstance(payload, dict):
        why = f"unreadable: {error or 'GitHub response missing'}"
        return {name: {"result": why, "url": None} for name in required}
    runs = payload.get("check_runs")
    if not isinstance(runs, list):
        return {
            name: {"result": "unreadable: malformed GitHub check response", "url": None}
            for name in required
        }
    latest: dict[str, dict] = {}
    for item in runs:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        name = item["name"]
        if name not in required:
            continue
        prev = latest.get(name)
        if not prev or (item.get("id") or 0) > (prev.get("id") or 0):
            latest[name] = item
    incomplete = (payload.get("total_count") or 0) > len(runs)
    result = {}
    for name in required:
        item = latest.get(name)
        if not item:
            state = (
                "unreadable: result pagination incomplete" if incomplete else "absent"
            )
            result[name] = {"result": state, "url": None}
        else:
            result[name] = {
                "result": item.get("conclusion")
                or item.get("status")
                or "unreadable: no check status",
                "url": item.get("html_url") or item.get("details_url"),
            }
    return result

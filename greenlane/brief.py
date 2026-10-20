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

    required = (status.get("main") or {}).get("required") or {}
    main_red = [k for k, v in required.items() if v not in GREEN]
    lost = (status.get("invariants") or {}).get("work_lost") or 0
    loud = bool(status.get("alarm") or main_red or lost or red or stuck)

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
    if main_red:
        parts.append(f"main is red on {', '.join(main_red)}")
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
    if not (main_red or lost or stuck or red):
        parts.append("all clear")

    return {
        "loud": loud,
        "landing": landing,
        "waiting": waiting,
        "stuck": stuck,
        "red": red,
        "main_red": main_red,
        "work_lost": lost,
        "summary": ". ".join(parts) + ".",
    }

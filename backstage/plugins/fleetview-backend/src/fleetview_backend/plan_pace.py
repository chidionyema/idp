"""How much work is left, from the claim's own pace -- and "unknown" when it has no pace.

Founder, 2026-10-23: "can we estimate based on goals and subgoals how much time or work left?"

A claim carries a plan: the issue body's `- [ ]` list is the sub-goals, and the claim comment's
timestamp is when the work started. Closed sub-goals per hour since then is the claim's own pace,
and the open ones at that pace is the time left. Two refusals are built in, because a number the
estate cannot stand behind is worse than no number:

* A claim that has closed nothing has no pace. It says "no pace yet" and no hours.
* A claim with no checklist has nothing to count. It says so, and no hours.

The output is a band, not a point. With three sub-goals closed, the sample is small enough that a
point estimate would be a guess wearing a number's clothes; +/-50% is the honest width, and the
basis string travels with the number so a reader can see what it was computed from.

This module is the ONE implementation of that arithmetic on the serving side. `bin/estate-work-status`
imports it (same repository) rather than keeping a second copy, and
`tests/test_plan_pace.py` fails if the two ever disagree.
"""

from __future__ import annotations

import re
from typing import Any

CHECKBOX = re.compile(r"(?m)^\s*[-*]\s+\[(?P<mark>[ xX])\]\s+(?P<text>.+?)\s*$")

# The band's half-width. Widening it would hide real progress; narrowing it would claim a
# precision a handful of sub-goals cannot support.
SPREAD = 0.5


def checklist(body: str | None) -> dict[str, Any]:
    """The plan as written: how many sub-goals are closed, how many exist, and the open ones."""
    done: list[str] = []
    open_: list[str] = []
    for m in CHECKBOX.finditer(body or ""):
        text = m.group("text").strip()
        (done if m.group("mark").lower() == "x" else open_).append(text)
    return {"done": len(done), "total": len(done) + len(open_), "open": open_}


def hours_phrase(h: float) -> str:
    if h < 1:
        return f"{int(round(h * 60))}m"
    if h < 48:
        return f"{h:.1f}h"
    return f"{h / 24:.1f}d"


def estimate(done: int, total: int, hours: float) -> dict[str, Any]:
    """Time left for a plan of `total` sub-goals with `done` closed after `hours`.

    Always returns the same keys, so a reader never has to guess whether a missing number means
    "no time left" or "no idea": `hours_left` is None when there is no pace, 0.0 when the plan is
    finished, and a positive number otherwise.
    """
    remaining = max(total - done, 0)
    if total <= 0:
        return {
            "pace_per_h": 0.0,
            "hours_left": None,
            "lo": None,
            "hi": None,
            "basis": "no sub-goals written, so there is nothing to pace",
        }
    if done <= 0:
        return {
            "pace_per_h": 0.0,
            "hours_left": None,
            "lo": None,
            "hi": None,
            "basis": f"no pace yet: 0 of {total} closed in {hours:.1f}h",
        }
    pace = done / max(hours, 1e-9)
    if remaining == 0:
        return {
            "pace_per_h": pace,
            "hours_left": 0.0,
            "lo": 0.0,
            "hi": 0.0,
            "basis": f"all {total} sub-goals closed in {hours:.1f}h",
        }
    hours_left = remaining / pace
    return {
        "pace_per_h": pace,
        "hours_left": hours_left,
        "lo": hours_left * (1 - SPREAD),
        "hi": hours_left * (1 + SPREAD),
        "basis": f"{done} of {total} closed in {hours:.1f}h (this claim's own pace)",
    }


def phrase(est: dict[str, Any]) -> str:
    """The estimate as one sentence a founder can read on a strip, or hear from Face."""
    left = est.get("hours_left")
    if left is None:
        return f"unknown -- {est.get('basis')}"
    if left <= 0:
        return f"none -- {est.get('basis')}"
    return (
        f"{hours_phrase(est['lo'])}-{hours_phrase(est['hi'])} left "
        f"({est.get('basis')}, +/-{int(SPREAD * 100)}%)"
    )

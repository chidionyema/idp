#!/usr/bin/env python3
"""bounds.py -- the decision core for adaptive executor time bounds.

THIS MODULE IS NOT WIRED. It is the pure decision half of the proposal in
`docs/proposals/2026-10-30-adaptive-executor-timeout-bounds.md`: it decides what a string bound
means and what the door should do about it, with no side effects, no network and no clock. The
wiring (the executor door, the receipt writer, the routing) is the next slice, and it must not
land before this core is proven by the tests in `tests/test_adaptive_bound_resolution.py`.

THE MEASURED PROBLEM (governed friction report, 2026-10-30T05:56:35Z).
2,375 recorded friction events: `refuse-ceiling` 229 of them. The agent writes `timeout 180`,
the door refuses because the hard cap is 100 seconds, and the agent has to discover the
decomposition by hand. Nine and a half percent of all friction is a door that cannot say what to
do instead of saying no.

THE MEASURED CONSTRAINT (executor jobs, measured 2026-10-30).
790 paired jobs: p50 0.6s, p75 4.0s, p90 14.1s, p95 25.9s, p99 58.9s, max 100.0s, with 4 jobs
killed at the ceiling (exit 124). The fixed 100-second cap is right for the overwhelming majority
of jobs and wrong only for a thin tail. Raising the cap would not help that tail, because the
tail is not slow -- it is slow AND long. So the cap stays at 100, and what changes is what the
door does with a request that does not fit.

THE THREE LAWS THIS CORE ENCODES.
1. The hard cap is 100 seconds and this module cannot exceed it, whatever the caller writes.
2. A caller never silently loses a bound it wrote, and never silently gains one it did not.
3. Learning is from observable outcomes only. A job that was KILLED at the ceiling is evidence
   that the ceiling was too small; it is never evidence that a larger bound would have worked.

THE GRAMMAR. A bound is a string.

    <digits>          exact seconds; honoured verbatim, clamped to the hard cap
    auto              the door measures this command shape and grants the measured p95
    quick | standard | deep
                      named classes: the door grants at most 10s / 30s / 60s, and may grant
                      less when the measurement says so
    range:<lo>..<hi>  an explicit window; the door grants at most <hi>
    need:<seconds>    "this work needs about <seconds>"; the door grants it when it fits under
                      the cap and ROUTES it to a door that can hold it when it does not
    none              no bound requested; the door applies its own default

Anything else is DENY. A bound that cannot be parsed is a bound that cannot be trusted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

# The hard boundary. `mcp/plugins/estate_executor.py` holds CEILING_SEC = 100; this constant
# mirrors it and `tests/test_adaptive_bound_resolution.py` proves the two agree.
HARD_CAP_SEC = 100
MIN_CEILING_SEC = 1

# The bound granted when nothing is known about the shape. Conservative on purpose: an
# unmeasured shape gets a short leash, not the maximum.
DEFAULT_UNMEASURED_SEC = 30

# The named classes. Each is a ceiling for that class; measurement may lower it, never raise it.
NAMED_CLASSES: Dict[str, int] = {"quick": 10, "standard": 30, "deep": 60}

# States. ALLOW is a grant. ROUTE is "not here, but here". DENY is a refusal. UNKNOWN is the
# state of a shape the door cannot measure: it still gets a conservative bound, and it is
# labelled UNKNOWN rather than dressed up as a measurement.
ALLOW = "ALLOW"
ROUTE = "ROUTE"
DENY = "DENY"
UNKNOWN = "UNKNOWN"

_DIGITS = re.compile(r"^\d+$")
_RANGE = re.compile(r"^range:(\d+)\.\.(\d+)$")
_NEED = re.compile(r"^need:(\d+)$")


@dataclass(frozen=True)
class Receipt:
    """One observed job. The only evidence the door is allowed to learn from."""

    shape: str
    elapsed_sec: float
    exit_code: int
    killed_at_ceiling: bool = False
    repo: str = ""


@dataclass(frozen=True)
class Resolution:
    state: str
    seconds: Optional[int]
    reason: str
    evidence: str = "none"  # "measured" | "none" | "caller"
    route: Optional[str] = None

    @property
    def effective(self) -> Optional[int]:
        """The seconds the door would actually grant. Never above the hard cap."""
        if self.seconds is None:
            return None
        return max(MIN_CEILING_SEC, min(self.seconds, HARD_CAP_SEC))


@dataclass(frozen=True)
class ParsedBound:
    kind: str  # "exact" | "auto" | "named" | "range" | "need" | "none"
    value: Optional[int] = None
    low: Optional[int] = None
    high: Optional[int] = None


def parse_bound(text: str) -> ParsedBound:
    """Parse the bound grammar. Unparseable input is a DENY, not a default."""
    if text is None:
        return ParsedBound(kind="none")
    raw = str(text).strip()
    if raw == "" or raw.lower() == "none":
        return ParsedBound(kind="none")
    if _DIGITS.match(raw):
        return ParsedBound(kind="exact", value=int(raw))
    if raw.lower() == "auto":
        return ParsedBound(kind="auto")
    lowered = raw.lower()
    if lowered in NAMED_CLASSES:
        return ParsedBound(kind="named", value=NAMED_CLASSES[lowered])
    m = _RANGE.match(raw)
    if m:
        low, high = int(m.group(1)), int(m.group(2))
        if low > high:
            return ParsedBound(kind="invalid")
        return ParsedBound(kind="range", low=low, high=high)
    m = _NEED.match(raw)
    if m:
        return ParsedBound(kind="need", value=int(m.group(1)))
    return ParsedBound(kind="invalid")


def percentile(values: Sequence[float], pct: float) -> float:
    """The nearest-rank percentile. No interpolation, so the answer is explainable."""
    if not values:
        raise ValueError("no values")
    ordered = sorted(values)
    if pct <= 0:
        return ordered[0]
    if pct >= 100:
        return ordered[-1]
    rank = max(1, int(round((pct / 100.0) * len(ordered) + 0.5)))
    return ordered[min(rank, len(ordered)) - 1]


def measured_bound(
    receipts: Iterable[Receipt], shape: str, repo: Optional[str] = None
) -> Optional[int]:
    """The p95 of the SUCCESSFUL runs of this shape, or None when there is nothing to learn from.

    Only successful runs count. A job killed at the ceiling proves the ceiling was too small; it
    does not prove a bigger ceiling would have been enough, so it is excluded from the
    measurement of what fits. Evidence is never pooled across repositories: a fast repository
    must not teach the slow one.
    """
    successes = [
        r.elapsed_sec
        for r in receipts
        if r.shape == shape
        and not r.killed_at_ceiling
        and r.exit_code == 0
        and (repo is None or not r.repo or r.repo == repo)
    ]
    if not successes:
        return None
    return int(round(percentile(successes, 95)))


def resolve(
    text: str,
    receipts: Sequence[Receipt] = (),
    shape: str = "",
    repo: Optional[str] = None,
    cap: int = HARD_CAP_SEC,
) -> Resolution:
    """Resolve a bound string into a decision. Pure: no clock, no filesystem, no network."""
    cap = max(MIN_CEILING_SEC, min(int(cap), HARD_CAP_SEC))
    parsed = parse_bound(text)

    if parsed.kind == "invalid":
        return Resolution(
            state=DENY,
            seconds=None,
            reason="the bound could not be parsed; a bound that cannot be read cannot be trusted",
        )

    if parsed.kind == "none":
        return Resolution(
            state=ALLOW,
            seconds=cap,
            reason="no bound was requested; the door applies its default",
            evidence="caller",
        )

    if parsed.kind == "exact":
        # A numeric bound the caller wrote is honoured exactly, up to the cap. It is never
        # rewritten and never rounded: 30 means 30.
        seconds = min(int(parsed.value or 0), cap)
        note = ""
        if int(parsed.value or 0) > cap:
            note = f"; the caller asked for {parsed.value}, the hard cap is {cap}"
        return Resolution(
            state=ALLOW,
            seconds=max(MIN_CEILING_SEC, seconds),
            reason=f"the caller asked for {parsed.value} seconds{note}",
            evidence="caller",
        )

    if parsed.kind == "named":
        ceiling = min(int(parsed.value or 0), cap)
        measured = measured_bound(receipts, shape, repo) if shape else None
        if measured is None:
            return Resolution(
                state=UNKNOWN,
                seconds=min(DEFAULT_UNMEASURED_SEC, ceiling),
                reason=(
                    f"the '{text}' class has no measured history for this shape; "
                    "a conservative bound is granted and labelled UNKNOWN"
                ),
                evidence="none",
            )
        seconds = max(MIN_CEILING_SEC, min(measured, ceiling))
        return Resolution(
            state=ALLOW,
            seconds=seconds,
            reason=(
                f"the '{text}' class measured p95 {measured}s for this shape; "
                f"granted {seconds}s (class ceiling {ceiling}s)"
            ),
            evidence="measured",
        )

    if parsed.kind == "range":
        high = min(int(parsed.high or 0), cap)
        low = max(MIN_CEILING_SEC, int(parsed.low or 0))
        if high < low:
            high = low
        measured = measured_bound(receipts, shape, repo) if shape else None
        if measured is None:
            return Resolution(
                state=UNKNOWN,
                seconds=min(DEFAULT_UNMEASURED_SEC, high),
                reason=(
                    "the range was requested but this shape has no measured history; "
                    "a conservative bound is granted and labelled UNKNOWN"
                ),
                evidence="none",
            )
        seconds = max(MIN_CEILING_SEC, min(measured, high))
        return Resolution(
            state=ALLOW,
            seconds=seconds,
            reason=(
                f"the measured p95 for this shape is {measured}s; granted {seconds}s "
                f"within the requested window {low}..{high}s"
            ),
            evidence="measured",
        )

    if parsed.kind == "need":
        need = int(parsed.value or 0)
        if need <= cap:
            return Resolution(
                state=ALLOW,
                seconds=max(MIN_CEILING_SEC, need),
                reason=f"the work needs about {need}s, which fits under the {cap}s cap",
                evidence="caller",
            )
        # It does not fit here. The answer is not "no": it is the door that can hold it.
        return Resolution(
            state=ROUTE,
            seconds=None,
            reason=(
                f"the work needs about {need}s, which does not fit under the {cap}s cap; "
                "run it on a door that can hold it"
            ),
            evidence="caller",
            route="background",
        )

    if parsed.kind == "auto":
        measured = measured_bound(receipts, shape, repo) if shape else None
        if measured is None:
            return Resolution(
                state=UNKNOWN,
                seconds=min(DEFAULT_UNMEASURED_SEC, cap),
                reason=(
                    "nothing is known about this shape yet; a conservative bound is granted "
                    "and labelled UNKNOWN"
                ),
                evidence="none",
            )
        seconds = max(MIN_CEILING_SEC, min(measured, cap))
        return Resolution(
            state=ALLOW,
            seconds=seconds,
            reason=f"the measured p95 for this shape is {measured}s; granted {seconds}s",
            evidence="measured",
        )

    # Unreachable: every kind is handled above. An unknown kind is a refusal, never a pass.
    return Resolution(
        state=DENY,
        seconds=None,
        reason=f"the bound kind '{parsed.kind}' is not implemented",
    )


def route_targets() -> List[str]:
    """The doors that can hold work the local ceiling cannot. Named, not guessed."""
    return [
        "background",  # the executor's detached job with a receipt
        "session",  # sb start / the Temporal session plane
        "lane",  # Greenlane: the work lands as a commit and CI carries it
    ]

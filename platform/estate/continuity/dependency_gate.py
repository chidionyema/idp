"""Greenlane dispatch wiring for the dependency-aware continuity engine.

A lane is a unit of work with declared upstream requirements. Greenlane
dispatches (pushes a lane so CI runs, or dispatches an agent-sandbox mission)
only when every declared upstream node of that lane is HEALTHY. Otherwise the
lane is PARKED_UPSTREAM before any runner, runner-second or CI minute is
spent, and the decision carries the blocking node and its evidence.

The adapter is deliberately small and dependency-free so it can be imported by
`greenlane/engine.py` without changing its import graph: load this module by
path (platform/ has no __init__.py, idp#3564) and call
`UpstreamFreezeGate(engine).before_dispatch(lane, dispatch=push_the_lane)`.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

from .dependency import HEALTHY, ContinuityEngine

PARKED_UPSTREAM = "PARKED_UPSTREAM"
DISPATCHED = "DISPATCHED"


@dataclass(frozen=True)
class Lane:
    name: str
    head: str
    requires: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Decision:
    lane: str
    head: str
    verdict: str
    blocked_by: Tuple[str, ...]
    evidence: Dict[str, str]
    dispatch_called: bool
    duration_us: float

    def as_dict(self) -> Dict[str, object]:
        return {
            "lane": self.lane,
            "head": self.head,
            "verdict": self.verdict,
            "blocked_by": list(self.blocked_by),
            "evidence": dict(self.evidence),
            "dispatch_called": self.dispatch_called,
            "duration_us": round(self.duration_us, 3),
        }


class UpstreamFreezeGate:
    """Pre-dispatch gate. `dispatch` is only invoked when nothing upstream is blocked."""

    def __init__(self, engine: ContinuityEngine) -> None:
        self.engine = engine

    def before_dispatch(self, lane: Lane, dispatch=None) -> Decision:
        t0 = time.perf_counter()
        blocked: List[str] = []
        evidence: Dict[str, str] = {}
        for node in lane.requires:
            state = self.engine.state.get(node)
            if state is None:
                # An unregistered requirement cannot be judged. Refuse (unknown != healthy).
                blocked.append(node)
                evidence[node] = "UNREGISTERED_REQUIREMENT"
            elif state != HEALTHY:
                blocked.append(node)
                evidence[node] = state
        if blocked:
            elapsed = (time.perf_counter() - t0) * 1e6
            return Decision(
                lane.name,
                lane.head,
                PARKED_UPSTREAM,
                tuple(blocked),
                evidence,
                False,
                elapsed,
            )
        if dispatch is not None:
            dispatch(lane)
        elapsed = (time.perf_counter() - t0) * 1e6
        return Decision(
            lane.name, lane.head, DISPATCHED, (), {}, dispatch is not None, elapsed
        )

    def dispatch_all(
        self, lanes: Sequence[Lane], dispatch=None
    ) -> Tuple[Decision, ...]:
        return tuple(self.before_dispatch(l, dispatch) for l in lanes)

"""Phase A — DAG runner with `graphlib` validation.

Every request through ZeroEdge and every search through TTCS instantiates a DAG
whose acyclicity is proven before a single CPU cycle runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from typing import Any, Callable, Iterable


@dataclass
class Stage:
    name: str
    deps: frozenset[str] = field(default_factory=frozenset)
    run: Callable[..., Any] | None = None


class TopologicalDAG:
    """A validated DAG. `prepare()` raises `CycleError` if acyclic."""

    def __init__(self, stages: Iterable[Stage]):
        self.stages: dict[str, Stage] = {s.name: s for s in stages}
        for s in self.stages.values():
            unknown = s.deps - self.stages.keys()
            if unknown:
                raise ValueError(f"stage {s.name!r} has unknown deps: {sorted(unknown)}")

    def validate(self) -> None:
        """Prove acyclicity. Raises `CycleError` on cycle."""
        ts = TopologicalSorter({s: self.stages[s].deps for s in self.stages})
        list(ts.static_order())  # static_order() calls prepare() internally

    def frontier(self, done: set[str]) -> list[str]:
        """Stages whose deps are all in `done`."""
        return [
            s.name for s in self.stages.values() if s.name not in done and s.deps.issubset(done)
        ]

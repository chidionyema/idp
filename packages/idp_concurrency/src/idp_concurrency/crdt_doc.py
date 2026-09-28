"""Phase D — Observed-Remove Set (OR-Set), a real CRDT in pure Python.

The OR-Set is one of the simplest CRDTs that satisfies the join-semilattice
properties the First-Principles doc demands. Two replicas can mutate the
same set concurrently and `merge()` resolves to a deterministic state — no
locks, no coordinator, no last-write-wins.

Algorithm:
    add(e)         -> tag a unique (replica_id, counter) to e
    remove(e)      -> tombstone every tag currently visible for e
    contains(e)    -> e has at least one live tag
    merge(other)   -> union of tags + tombstones

The merge is monotonic: tags and tombstones are added, never removed.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class _Tag:
    replica: str
    counter: int

    def key(self) -> tuple[str, int]:
        return (self.replica, self.counter)


@dataclass
class ORSet:
    """Observed-Remove Set, monotonic per replica."""

    replica_id: str
    tags: dict[str, set[_Tag]] = field(default_factory=dict)  # element -> tags
    tombstones: set[_Tag] = field(default_factory=set)

    _counter: itertools.count = field(default_factory=itertools.count, init=False, repr=False)

    def _next_tag(self) -> _Tag:
        return _Tag(self.replica_id, next(self._counter))

    def add(self, element: str) -> _Tag:
        tag = self._next_tag()
        self.tags.setdefault(element, set()).add(tag)
        return tag

    def remove(self, element: str) -> None:
        for tag in self.tags.get(element, ()):
            self.tombstones.add(tag)

    def discard(self, element: str) -> None:
        """Remove only if currently present (no exception otherwise)."""
        if element in self.tags:
            self.remove(element)

    def __contains__(self, element: str) -> bool:
        live = self.tags.get(element, set()) - self.tombstones
        return bool(live)

    def __iter__(self) -> Iterable[str]:
        for element, tags in self.tags.items():
            if tags - self.tombstones:
                yield element

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def merge(self, other: "ORSet") -> "ORSet":
        """Idempotent, commutative, associative."""
        merged = ORSet(self.replica_id)
        merged.tags = {e: set(tags) for e, tags in self.tags.items()}
        for element, tags in other.tags.items():
            merged.tags.setdefault(element, set()).update(tags)
        merged.tombstones = self.tombstones | other.tombstones
        max_counter = -1
        for tags in merged.tags.values():
            for tag in tags:
                if tag.replica == self.replica_id and tag.counter > max_counter:
                    max_counter = tag.counter
        merged._counter = itertools.count(max_counter + 1)
        return merged

    def state(self) -> dict[str, list[str]]:
        """A JSON-safe view of the current live set."""
        return sorted(e for e in self)


__all__ = ["ORSet"]

"""Shadow memory with CRDT-backed storage.

The `ShadowMemory` API is unchanged; the underlying store is an `ORSet` so two
replicas of the harness can converge on the same set of (action, result,
takeaway) triplets without locks.

The element key is `f"{created_at}|{counter}|{symbol}"` to guarantee uniqueness
across replicas with the same wall-clock. `top_k` filters by symbol and sorts
by `created_at` desc — the OR-Set doesn't preserve insertion order, so the
sort happens on read.
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field

from idp_concurrency.crdt_doc import ORSet

_TRIPLET_KEY_SEP = "\x1f"  # ASCII Unit Separator; never in payload


@dataclass
class Triplet:
    action: str
    result: str
    takeaway: str
    symbol: str = ""
    negative: bool = False
    created_at: int = field(default_factory=lambda: int(time.time()))

    def key(self, counter: int) -> str:
        return _TRIPLET_KEY_SEP.join(
            (
                str(self.created_at),
                str(counter),
                self.symbol,
                self.action,
                self.result,
            )
        )

    @classmethod
    def from_key(cls, key: str) -> tuple[int, str, str, str]:
        created_at, counter, symbol, action, result = key.split(_TRIPLET_KEY_SEP)
        return int(created_at), symbol, action, result


class ShadowMemory:
    """API-compatible with the original list-backed implementation."""

    def __init__(self, replica_id: str = "default") -> None:
        self._replica_id = replica_id
        self._store: ORSet = ORSet(replica_id=replica_id)
        self._counter = itertools.count()
        self._triplets: dict[str, Triplet] = {}  # key -> Triplet (lossless)

    def add(self, action: str, result: str, takeaway: str, symbol: str = "") -> None:
        t = Triplet(action=action, result=result, takeaway=takeaway, symbol=symbol)
        self._add(t)

    def add_negative(self, summary: str, symbol: str = "") -> None:
        t = Triplet(
            action="verification",
            result="failed",
            takeaway=summary,
            symbol=symbol,
            negative=True,
        )
        self._add(t)

    def _add(self, t: Triplet) -> None:
        counter = next(self._counter)
        key = t.key(counter)
        self._triplets[key] = t
        self._store.add(key)

    def top_k(self, symbol: str, k: int = 8) -> list[Triplet]:
        items: list[Triplet] = []
        for key in self._store:
            parts = key.split(_TRIPLET_KEY_SEP)
            # key format: created_at | counter | symbol | action | result
            if len(parts) != 5:
                continue
            if symbol and parts[2] != symbol:
                continue
            if key in self._triplets:
                items.append((int(parts[1]), self._triplets[key]))
        items.sort(key=lambda pair: (pair[1].created_at, pair[0]), reverse=True)
        return [t for _, t in items[:k]]

    def truncate_to(self, version: int) -> None:
        """Keep only the first `version` triplets (CRDT-safe).

        Semantics: matches the original list-backed `truncate_to`. Anything
        beyond `version` is tombstoned in the CRDT; `version >= len()` is a
        no-op.
        """
        if version < 0:
            raise ValueError("version must be >= 0")
        ordered = sorted(
            self._triplets.items(), key=lambda kv: (kv[1].created_at, _key_counter(kv[0]))
        )
        for key, _ in ordered[version:]:
            self._store.remove(key)

    def merge(self, other: "ShadowMemory") -> "ShadowMemory":
        merged = ShadowMemory(replica_id=self._replica_id)
        # Triplets are immutable values keyed by (created_at, counter, ...);
        # merging two replicas is the union of (key -> Triplet) plus the
        # CRDT store, both of which are commutative + idempotent.
        for key, t in self._triplets.items():
            merged._triplets[key] = t
        for key, t in other._triplets.items():
            merged._triplets[key] = t
        merged._store = self._store.merge(other._store)
        return merged

    def __len__(self) -> int:
        return len(self._store)


def _key_counter(key: str) -> int:
    parts = key.split(_TRIPLET_KEY_SEP)
    return int(parts[1]) if len(parts) == 5 else 0


__all__ = ["ShadowMemory", "Triplet"]

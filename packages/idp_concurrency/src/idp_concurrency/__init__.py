"""idp_concurrency — shared primitives for ZeroEdge, TTCS, and the rest of the estate.

This package is the single home for:

  * Phase A — `dag.TopologicalDAG` (graphlib-validated DAG runner)
  * Phase B — `task_scope.scoped_task_group` (anyio TaskGroup wrapper)
  * Phase C — `waitfree_queue.WaitFreeQueue`, `tracer.TracedClient`
  * Phase D — `merkle_log.MerkleLog` (SQLite WAL + SHA-256 chain), `crdt_doc.CRDTDoc`

It also ships the four forcing-function lint rules under `lint/`:

  * `lint.no_locks`       — Forcing F1: no threading.Lock / RLock / Event / Semaphore
  * `lint.no_unbounded`   — Forcing F2: asyncio.create_task only inside TaskGroup
  * `lint.no_untraced`    — Forcing F3: bare httpx / aiohttp / requests banned
  * `lint.no_ad_hoc`      — Forcing F4: protocol coordination requires a TLA+ spec

Anything in either repo that needs concurrency or state goes through this package.
Inline `threading.Lock()`, `asyncio.create_task()`, or `httpx.post()` calls
outside `idp_concurrency.tracer` are build-time violations.
"""

from __future__ import annotations

__version__ = "0.1.0"

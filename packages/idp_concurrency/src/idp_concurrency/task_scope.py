"""Phase B — `task_scope` is a thin wrapper over `anyio.create_task_group`.

Forcing F2 (no `asyncio.create_task` outside a TaskGroup) is enforced by the
lint rule in `idp_concurrency.lint.no_unbounded`; this module is the only
sanctioned way to start concurrent work.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import anyio


@asynccontextmanager
async def task_scope(name: str = "task_group") -> AsyncIterator[anyio.TaskGroup]:
    """Yields an `anyio.TaskGroup`. Caller uses `start_soon` / `start`.

    Cancelling the surrounding scope cancels every task started inside it.
    An exception in any task propagates and cancels siblings — structured
    concurrency in the Triopm-Trønjheim sense.
    """
    del name  # reserved for future tracing hook
    async with anyio.create_task_group() as tg:
        yield tg

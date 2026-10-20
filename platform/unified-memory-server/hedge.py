"""A hedged call: the first answer from a few staggered attempts, inside one deadline.

WHY. 2026-10-20, measured from the router pod against integrate.api.nvidia.com, the upstream of
the `embed-query` lane: of 8 direct embedding calls, 4 answered in 0.08-0.27 s and 4 sent nothing
back at all until the 20 s client timeout. Both of the host's IPs did it (5 pinned calls each:
2 and 3 hangs), TCP connects in 0.00 s, and the router adds nothing -- the same split shows
calling NIM directly. A hang is per request, not per minute: the next call is as likely to
answer in 0.1 s as the last.

/memories/brief embedded its task with one such call under EMBED_TIMEOUT_S (20 s). So half of all
briefs took 20 s and came back with search_by_meaning false, and the router's Active Memory
callback, which gives the brief 1.5 s, got NOTHING -- not even the recent half that needs no
vector, because that half waits for the embed. Measured: one router chat call, `active_memory
brief unreadable ... timed out`, no block injected.

Waiting longer cannot fix a request that will never answer; asking again can. Attempt i starts at
i * hedge_s unless an earlier one has already answered, and the first non-None answer wins. With
a hang rate p, n attempts miss with p**n (0.5 -> 0.125 for 3). A miss costs `deadline_s`, after
which the caller does what it already did on a down lane: the brief returns its recent half.

Pure stdlib on purpose: main.py needs fastapi and psycopg and cannot be imported by a unit test.
"""

from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Callable, Optional, TypeVar

T = TypeVar("T")


def first_answer(
    call: Callable[[float], Optional[T]],
    attempts: int,
    hedge_s: float,
    deadline_s: float,
) -> Optional[T]:
    """The first non-None `call(timeout)` among up to `attempts` staggered tries, or None.

    `call` receives the seconds left until the deadline, so an attempt never outlives it and a
    hung one ends with the request instead of holding a thread for its own longer timeout.
    """
    attempts = max(1, attempts)
    start = time.monotonic()
    pool = ThreadPoolExecutor(max_workers=attempts)
    pending: set = set()
    try:
        for i in range(attempts):
            left = deadline_s - (time.monotonic() - start)
            if left <= 0:
                break
            pending.add(pool.submit(call, left))
            # Wait for an answer until the next attempt is due; after the last, the deadline.
            until = (
                deadline_s if i == attempts - 1 else min(deadline_s, (i + 1) * hedge_s)
            )
            while pending:
                left = until - (time.monotonic() - start)
                if left <= 0:
                    break
                done, pending = wait(pending, timeout=left, return_when=FIRST_COMPLETED)
                for f in done:
                    # an attempt that raised is a miss, the same as one that returned None
                    if f.exception() is None and f.result() is not None:
                        return f.result()
        return None
    finally:
        # A straggler is not waited for: it is bounded by the timeout it was handed.
        pool.shutdown(wait=False, cancel_futures=True)

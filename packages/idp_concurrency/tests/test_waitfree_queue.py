"""Concurrent stress tests for WaitFreeQueue.

The contract we prove:
  * Every pushed item is delivered to exactly one pop.
  * No item is dropped or duplicated under contention.
  * The native Rust-backed queue (crossbeam::SegQueue) is used when present.
  * The pure-Python deque fallback works under the GIL.
  * Stress with 16 producers × 16 consumers × 1000 items each.
"""

from __future__ import annotations

import threading
import time
from collections import Counter

import pytest

from idp_concurrency.waitfree_queue import (
    HAS_NATIVE_ATOMICS,
    IS_FREE_THREADED,
    WaitFreeQueue,
)


def test_native_or_fallback_in_use():
    q = WaitFreeQueue()
    if HAS_NATIVE_ATOMICS:
        assert q.is_native is True
    else:
        assert q.is_native is False
        if IS_FREE_THREADED:
            pytest.fail("free-threaded runtime without native atomics should have crashed")


def test_single_producer_consumer():
    q: WaitFreeQueue[int] = WaitFreeQueue()
    for i in range(100):
        q.push(i)
    out = [q.pop() for _ in range(100)]
    assert out == list(range(100))
    assert q.pop() is None


def test_fifo_within_producer():
    """A single thread that pushes then pops must see FIFO order."""
    q: WaitFreeQueue[int] = WaitFreeQueue()
    for i in range(50):
        q.push(i)
    out = [q.pop() for _ in range(50)]
    assert out == list(range(50))


def test_many_producers_consumers_no_loss_no_duplication():
    n_producers = 16
    n_consumers = 16
    items_per_producer = 1000
    expected_total = n_producers * items_per_producer

    q: WaitFreeQueue[tuple[int, int]] = WaitFreeQueue()
    consumed: list[tuple[int, int]] = []
    consumed_lock = threading.Lock()
    stop = threading.Event()

    def producer(pid: int) -> None:
        for i in range(items_per_producer):
            q.push((pid, i))

    def consumer(cid: int) -> None:
        local: list[tuple[int, int]] = []
        while not stop.is_set() or len(q) > 0:
            item = q.pop()
            if item is None:
                time.sleep(0.0001)
                if stop.is_set() and len(q) == 0:
                    break
                continue
            local.append(item)
        with consumed_lock:
            consumed.extend(local)

    producers = [threading.Thread(target=producer, args=(i,)) for i in range(n_producers)]
    consumers = [threading.Thread(target=consumer, args=(i,)) for i in range(n_consumers)]

    for c in consumers:
        c.start()
    for p in producers:
        p.start()
    for p in producers:
        p.join()
    stop.set()
    for c in consumers:
        c.join(timeout=5)
        if c.is_alive():
            pytest.fail(f"consumer did not stop within 5s; queue len={len(q)}")

    counts = Counter(consumed)
    assert len(consumed) == expected_total, f"got {len(consumed)}, expected {expected_total}"
    assert max(counts.values()) == 1, f"duplicate: {counts.most_common(1)}"
    expected = {(p, i) for p in range(n_producers) for i in range(items_per_producer)}
    assert set(consumed) == expected


def test_push_pop_concurrent_basic():
    """Smoke test under moderate concurrency."""
    q: WaitFreeQueue[int] = WaitFreeQueue()
    n = 5000

    def push_all() -> None:
        for i in range(n):
            q.push(i)

    def pop_all() -> list[int]:
        out: list[int] = []
        while len(out) < n:
            item = q.pop()
            if item is not None:
                out.append(item)
        return out

    t1 = threading.Thread(target=push_all)
    t2 = threading.Thread(target=pop_all)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert q.is_empty()


def test_free_threaded_tripwire_blocks_naive_fallback():
    """If somehow the tripwire were disabled, this would corrupt under FT."""
    # This is a smoke test that the tripwire logic at import time raises.
    # We don't actually run it — we just import the module and check the flag.
    from idp_concurrency import waitfree_queue as wq

    # The module either loaded successfully (HAS_NATIVE or GIL-on) or raised.
    # If we're here, the contract held.
    assert isinstance(wq.HAS_NATIVE_ATOMICS, bool)
    assert isinstance(wq.IS_FREE_THREADED, bool)
    assert not (wq.IS_FREE_THREADED and not wq.HAS_NATIVE_ATOMICS), (
        "free-threaded runtime without native atomics must crash at import"
    )

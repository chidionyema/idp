"""Phase C — concurrent MPMC queue, hardware-backed via crossbeam.

The native implementation lives in the `idp_atomics` PyO3 extension, which
wraps `crossbeam::queue::SegQueue` for true lock-free progress across physical
cores. On a free-threaded Python 3.13t/3.14t build, `push` and `pop` release
the GIL and execute against atomic CAS in the Rust process.

On a GIL-enabled build (3.9–3.12), the same code still works — the queue
itself is lock-free — but the interpreter serializes bytecode. The
free-threaded tripwire at the bottom of this file refuses to fall back to a
GIL-dependent queue when the runtime is free-threaded but the native
extension is absent: that combination would be a correctness disaster.
"""

from __future__ import annotations

import sys
from typing import Generic, Optional, TypeVar

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Detect the free-threaded build BEFORE importing the native extension.
#
# `sys._is_gil_enabled()` is the documented CPython 3.13+ probe. On earlier
# interpreters the attribute is absent and we assume GIL-on.


def _is_free_threaded() -> bool:
    getter = getattr(sys, "_is_gil_enabled", None)
    if getter is None:
        return False
    try:
        return not getter()
    except Exception:
        return False


def _load_native():
    try:
        from idp_atomics import WaitFreeQueue as _WQ

        return _WQ
    except Exception:
        return None


_NATIVE = _load_native()
IS_FREE_THREADED = _is_free_threaded()
HAS_NATIVE_ATOMICS = _NATIVE is not None


# ---------------------------------------------------------------------------
# Free-threaded tripwire: refuse to silently degrade to a GIL-dependent
# implementation when the runtime is GIL-less and the extension is absent.

if IS_FREE_THREADED and not HAS_NATIVE_ATOMICS:
    raise RuntimeError(
        "FATAL: running free-threaded Python (GIL disabled) without "
        "idp_atomics (Rust/PyO3). The Python-only fallback uses "
        "collections.deque, which is NOT thread-safe under the no-GIL "
        "build and would cause catastrophic memory corruption. "
        "Build the native extension with: "
        "  cd idp/packages/idp_atomics && VIRTUAL_ENV=$(which python) maturin develop --release"
    )


# ---------------------------------------------------------------------------
# Pure-Python fallback (deque-based). Lock-free only under the GIL.
#
# This is the only path on a GIL-enabled interpreter when the native
# extension is absent, e.g. a clean source checkout before `maturin develop`.


class _DequeQueue(Generic[T]):
    """Sharded-by-thread fallback. Same shape as the historical pure-Python impl."""

    def __init__(self) -> None:
        from collections import deque

        self._q: "deque[T]" = deque()

    def push(self, item: T) -> None:
        self._q.append(item)

    def pop(self) -> Optional[T]:
        from collections import deque as _dq

        try:
            return self._q.popleft()
        except IndexError:
            return None

    def is_empty(self) -> bool:
        return not self._q

    def len(self) -> int:
        return len(self._q)

    def is_native(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Public API


class WaitFreeQueue(Generic[T]):
    """MPMC queue. Native (crossbeam + CAS) when `idp_atomics` is built;
    sharded-deque fallback only when the GIL is present."""

    def __init__(self) -> None:
        if _NATIVE is not None:
            self._q = _NATIVE()
            self._is_native = True
        else:
            self._q = _DequeQueue()
            self._is_native = False

    def push(self, item: T) -> None:
        self._q.push(item)

    def pop(self) -> Optional[T]:
        return self._q.pop()

    def is_empty(self) -> bool:
        return self._q.is_empty()

    def __len__(self) -> int:
        return self._q.len()

    @property
    def is_native(self) -> bool:
        """True iff backed by the Rust extension. Cheap to query."""
        return self._is_native

    @property
    def free_threaded_runtime(self) -> bool:
        """True iff this Python process has the GIL disabled."""
        return IS_FREE_THREADED


__all__ = ["WaitFreeQueue", "HAS_NATIVE_ATOMICS", "IS_FREE_THREADED"]

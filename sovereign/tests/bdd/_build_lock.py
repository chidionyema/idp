"""Build the acceptance graph once, even when the suite runs on several workers.

`test_estate_twin.py` builds `catalog/estate.db` from the estate's own builders when a fresh
checkout has none, and CI runs the suite as `pytest tests/bdd -n auto`: four xdist workers, each
with its own process tree, each reaching a `_db()` step within milliseconds of the others. The
guard on the build was `if ASSET_DB.exists(): return`, which is false for all four at that
moment -- so all four ran the builders at once: four twin sweeps, 526 `git` processes each, all
writing the same SQLite file. A build that should be paid once per suite was paid four times,
which is how one slow build became a SIGKILL at the 180s cap (CI 2026-10-11, job 114542690924:
"1 failed, 371 passed", the one failure a `subprocess.TimeoutExpired` on the twin while the
other workers passed against whichever build won).

`flock` is the primitive, not a pid file and not a "building" marker on disk: the kernel drops
the lock when the holder exits for ANY reason, so a builder that is SIGKILLed -- the exact
failure this is here to stop repeating -- cannot leave the rest of the suite waiting on a lock
nobody holds. A pid file can, and that would trade a flake for a hang.

The wait is bounded anyway, and on expiry the caller builds rather than blocking: the worst case
is the concurrency this file exists to avoid, never a suite that cannot finish.
"""

from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path
from typing import Callable

LOCK_NAME = ".graph-build.lock"

# Long enough for a cold build on a loaded runner, short enough that a wedged holder cannot
# hold the suite past its own timeout.
WAIT_S = 240.0

POLL_S = 0.5


def build_once(
    asset_db: Path,
    builds: Callable[[], None],
    wait_s: float = WAIT_S,
    _sleep: Callable[[float], None] = time.sleep,
    _now: Callable[[], float] = time.monotonic,
) -> None:
    """Call `builds` exactly once across the processes racing to build `asset_db`.

    The first process in runs `builds`; the others wait on the lock, then find the database
    already on disk and return without building. A build that leaves no database behind is not
    hidden here: every caller checks for the file itself and fails loudly.
    """
    lock = asset_db.parent / LOCK_NAME
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        deadline = _now() + wait_s
        held = False
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held = True
                break
            except OSError:
                if _now() >= deadline:
                    break
                _sleep(POLL_S)
        if held and asset_db.exists():
            # Another worker built it while this one waited for the lock.
            return
        builds()
    finally:
        os.close(fd)

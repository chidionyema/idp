"""The acceptance graph is built once per suite, not once per xdist worker.

CI runs `pytest tests/bdd -q -n auto`: four workers, each with its own processes. Seven scenarios
in `test_estate_twin.py` need the graph, and every worker that reaches one calls `_build_graph()`
within milliseconds of the others, when `catalog/estate.db` does not exist yet -- so all four ran
`bin/db-gen` and `bin/estate-twin-runtime --once --code --domains` at once, four sweeps writing
the same SQLite file. One of them was SIGKILLed at the 180s cap while the rest passed against
whichever build won (CI 2026-10-11, job 114542690924: "1 failed, 371 passed").

These tests grade `sovereign/tests/bdd/_build_lock.py`, the code the suite actually calls.

Run:
    pytest tests/test_the_accepted_graph_is_built_once.py -v
"""

from __future__ import annotations

import fcntl
import importlib.machinery
import importlib.util
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BDD = ROOT / "sovereign" / "tests" / "bdd"

# A worker standing in for the real one: it registers the build, sleeps like a sweep, then
# leaves a database behind.
DRIVER = """
import sys, time
from pathlib import Path

sys.path.insert(0, {bdd!r})
from _build_lock import build_once

asset_db, counter, sleep_s = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])


def builds():
    with counter.open("a") as fh:
        fh.write("build\\n")
    time.sleep(sleep_s)
    asset_db.parent.mkdir(parents=True, exist_ok=True)
    asset_db.write_text("graph")


build_once(asset_db, builds)
"""

# The same worker, except the database is on disk for the WHOLE build -- which is what
# `bin/db-gen` does: it creates catalog/estate.db and `bin/estate-twin-runtime` fills it in
# afterwards. A caller that treats `exists()` as ready reads the half-written graph.
EARLY_DRIVER = """
import sys, time
from pathlib import Path

sys.path.insert(0, {bdd!r})
from _build_lock import build_once

asset_db, counter, sleep_s = Path(sys.argv[1]), Path(sys.argv[2]), float(sys.argv[3])


def builds():
    asset_db.parent.mkdir(parents=True, exist_ok=True)
    asset_db.write_text("half")
    with counter.open("a") as fh:
        fh.write("build\\n")
    time.sleep(sleep_s)
    asset_db.write_text("graph")


build_once(asset_db, builds)
print(asset_db.read_text() if asset_db.exists() else "<no database>")
"""


def _lock():
    loader = importlib.machinery.SourceFileLoader(
        "build_lock_under_test", str(BDD / "_build_lock.py")
    )
    spec = importlib.util.spec_from_loader("build_lock_under_test", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _spawn(db: Path, counter: Path, sleep_s: float) -> subprocess.Popen:
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            DRIVER.format(bdd=str(BDD)),
            str(db),
            str(counter),
            str(sleep_s),
        ]
    )


def test_four_workers_racing_build_the_graph_once(tmp_path):
    """The whole point: four processes, one build."""
    db = tmp_path / "catalog" / "estate.db"
    counter = tmp_path / "builds.txt"

    workers = [_spawn(db, counter, 2.0) for _ in range(4)]
    codes = [w.wait(timeout=120) for w in workers]

    assert codes == [0, 0, 0, 0]
    assert counter.read_text().splitlines() == ["build"], (
        "the graph was built once per worker; on a cold checkout that is four twin sweeps at "
        "once, which is what the 180s cap SIGKILLs"
    )
    assert db.read_text() == "graph", "the waiting workers left without a graph to read"


def test_a_builder_killed_holding_the_lock_does_not_wedge_the_suite(tmp_path):
    """SIGKILL is the failure being fixed; it must not turn a flake into a hang."""
    db = tmp_path / "catalog" / "estate.db"
    counter = tmp_path / "builds.txt"

    victim = _spawn(db, counter, 30.0)
    deadline = time.monotonic() + 30
    while not counter.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert counter.exists(), "the first worker never reached its build"
    os.kill(victim.pid, signal.SIGKILL)
    victim.wait(timeout=30)

    survivor = _spawn(db, counter, 0.1)
    started = time.monotonic()
    assert survivor.wait(timeout=60) == 0
    elapsed = time.monotonic() - started

    assert elapsed < 30, (
        f"a worker waited {elapsed:.1f}s on a lock whose holder was killed; the kernel drops an "
        "flock when the holder dies, so nothing should have to wait"
    )
    assert counter.read_text().splitlines() == ["build", "build"], (
        "the survivor did not rebuild after the killed worker left no graph behind"
    )
    assert db.read_text() == "graph"


def test_a_wait_that_expires_builds_rather_than_hanging(tmp_path):
    """A wedged holder costs a duplicate build, never a suite that cannot finish."""
    module = _lock()
    db = tmp_path / "catalog" / "estate.db"
    lock = db.parent / module.LOCK_NAME
    lock.parent.mkdir(parents=True, exist_ok=True)

    holder = os.open(lock, os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(holder, fcntl.LOCK_EX)
    try:
        built: list[int] = []
        started = time.monotonic()
        module.build_once(
            db, lambda: built.append(1), wait_s=0.3, _sleep=lambda _s: None
        )
        elapsed = time.monotonic() - started
    finally:
        os.close(holder)

    assert built == [1], (
        "the caller neither built nor returned while another process held the lock"
    )
    assert elapsed < 5, (
        f"build_once blocked for {elapsed:.1f}s instead of giving up on the wait"
    )


def test_a_database_that_appears_mid_build_is_not_ready(tmp_path):
    """`exists()` is not "built": the file is on disk for the whole of a build.

    The gap between the file appearing and the graph being finished is a real read window, not a
    theory: CI 2026-10-11 reported it as `sqlite3.OperationalError: database is locked` at
    test_estate_twin.py:368. Readiness is decided under the lock, never before it.
    """
    db = tmp_path / "catalog" / "estate.db"
    counter = tmp_path / "builds.txt"

    first = subprocess.Popen(
        [
            sys.executable,
            "-c",
            EARLY_DRIVER.format(bdd=str(BDD)),
            str(db),
            str(counter),
            "2.0",
        ],
        stdout=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 30
    while not db.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    assert db.exists(), "the first builder never put the database on disk"

    started = time.monotonic()
    second = subprocess.Popen(
        [
            sys.executable,
            "-c",
            EARLY_DRIVER.format(bdd=str(BDD)),
            str(db),
            str(counter),
            "0.1",
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    handed, _ = second.communicate(timeout=60)
    elapsed = time.monotonic() - started
    assert first.wait(timeout=60) == 0

    assert counter.read_text().splitlines() == ["build"], (
        "a caller saw the half-written database, called it ready and built again"
    )
    assert handed.strip() == "graph", (
        f"the caller left holding {handed.strip()!r}: it took the database while another worker "
        "was still writing it"
    )
    assert elapsed >= 1.0, (
        f"the second caller returned after {elapsed:.1f}s while the first was still building, so "
        "it read a graph that was still being written"
    )


def test_the_lock_lives_beside_the_graph(tmp_path):
    """One lock per graph, so two checkouts never serialise against each other."""
    module = _lock()
    db = tmp_path / "catalog" / "estate.db"
    module.build_once(db, lambda: db.write_text("graph"))
    assert (tmp_path / "catalog" / module.LOCK_NAME).exists()
    assert not (ROOT / module.LOCK_NAME).exists(), (
        "the lock was written into the repository root, where every checkout and every suite "
        "would share it"
    )

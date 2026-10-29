"""The estate's worker pool, tested.

The pool boots workers; each worker claims a task from the queue, runs it in its own
worktree and completes it.

The defect this module was written for: the worker loop's `from platform.queue import
dispatcher` raised ModuleNotFoundError ("'platform' is not a package" -- platform/ has no
__init__.py because it collides with the stdlib `platform` module, idp#3564). The loop
caught the error, logged it and died, so the pool had never claimed a task: the estate's
parallel execution substrate was inert.

These tests drive the real pool against a real queue, in a real git repository.
"""

from __future__ import annotations

import asyncio
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, dotted: str):
    """Load a module of platform/ by path.

    platform/ has no __init__.py: it collides with the stdlib `platform` module the
    moment anything imports it bare (idp#3564), and pytest imports `platform` at
    startup. The modules are loaded by path under their real dotted names instead.
    """
    if dotted in sys.modules:
        return sys.modules[dotted]
    spec = importlib.util.spec_from_file_location(dotted, str(REPO_ROOT / rel))
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = module
    spec.loader.exec_module(module)
    return module


_queue_package = _load("platform/queue/__init__.py", "platform.queue")
dispatcher = _queue_package.load_dispatcher()
worker_pool = _load(
    "platform/execution/worker_pool.py", "platform.execution.worker_pool"
)
WorkerPool = worker_pool.WorkerPool


@pytest.fixture
def repo(tmp_path):
    """A real git repository with one commit in it."""
    path = tmp_path / "repo"
    path.mkdir()
    for args in (
        ["init", "--quiet"],
        ["config", "user.email", "agent@estate"],
        ["config", "user.name", "agent"],
    ):
        subprocess.run(["git"] + args, cwd=str(path), check=True, capture_output=True)
    (path / "README.md").write_text("the estate\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(path), check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "the estate"],
        cwd=str(path),
        check=True,
        capture_output=True,
    )
    return path


@pytest.fixture
def queue(tmp_path, repo, monkeypatch):
    """A queue in a temp directory, with the environment the dispatcher reads."""
    monkeypatch.setenv("QUEUE_DB_PATH", str(tmp_path / "state" / "queue.db"))
    monkeypatch.setenv("WORKTREE_BASE", str(tmp_path / "wt"))
    monkeypatch.setenv("IDP_ROOT", str(repo))
    monkeypatch.setenv("WORKTREE_ARCHIVE_ROOT", str(tmp_path / "quarantine"))
    dispatcher.init_db()
    return dispatcher


# ---------------------------------------------------------------------------
# the pool
# ---------------------------------------------------------------------------


def test_the_pool_boots_its_workers():
    """Booting makes the workers and says so."""
    pool = WorkerPool(n_workers=3)
    pool.boot()

    status = pool.get_status()
    assert status["pool_size"] == 3
    assert len(status["workers"]) == 3
    assert status["active_workers"] == 0
    assert status["total_tasks_completed"] == 0
    assert pool.active is True


def test_the_pool_is_bounded_by_its_maximum():
    """Ten workers is the estate's bound, and the pool says so."""
    pool = WorkerPool(n_workers=50, max_workers=10)
    assert pool.n_workers == 10

    pool.boot()
    pool.scale(50)
    assert pool.n_workers == 10
    assert len(pool.workers) == 10


def test_the_pool_scales_up_and_down_gracefully():
    """Scaling up adds workers; scaling down marks the excess to finish their task."""
    pool = WorkerPool(n_workers=2)
    pool.boot()

    pool.scale(4)
    assert len(pool.workers) == 4

    pool.scale(2)
    assert pool.n_workers == 2
    marked = [w for w in pool.workers.values() if w.get("graceful_shutdown")]
    assert len(marked) == 2


def test_shutdown_stops_the_pool():
    """Shutdown is a signal: the workers finish what they hold and stop."""
    pool = WorkerPool(n_workers=1)
    pool.boot()
    pool.shutdown()
    assert pool.active is False


# ---------------------------------------------------------------------------
# the worker loop, end to end
# ---------------------------------------------------------------------------


def test_the_pool_can_reach_the_queue():
    """The worker loop's first act is to reach the queue.

    It used to be `from platform.queue import dispatcher`, which raises
    ModuleNotFoundError in this repository, so every worker died on its first cycle.
    """
    module = worker_pool._queue_dispatcher()
    assert module is dispatcher
    for name in (
        "init_db",
        "push_task",
        "claim_task",
        "complete_task",
        "sweep_zombies",
    ):
        assert hasattr(module, name)


def test_a_worker_claims_a_task_runs_it_in_a_worktree_and_completes_it(queue):
    """The whole loop, against the real queue."""
    queue.push_task("prove the thing")
    seen = {}
    pool = WorkerPool(n_workers=1)

    async def orchestrator(goal, worktree=None):
        seen["goal"] = goal
        seen["worktree"] = worktree
        # the agent works in a real worktree of the real repository
        assert Path(worktree).exists()
        (Path(worktree) / "NOTES.md").write_text("the work\n")
        return {"ok": True}

    async def scenario():
        pool.boot()
        runner = asyncio.create_task(pool.run_workers(orchestrator_fn=orchestrator))
        for _ in range(100):
            await asyncio.sleep(0.1)
            if pool.get_status()["total_tasks_completed"]:
                break
        pool.shutdown()
        await asyncio.wait_for(runner, timeout=30)

    asyncio.run(scenario())

    assert seen["goal"] == "prove the thing"
    assert seen["worktree"], "the worker ran the task without a worktree"
    row = queue.get_task_list()[0]
    assert row[2] == "success"
    assert pool.get_status()["total_tasks_completed"] == 1


def test_a_worker_that_fails_marks_the_task_failed(queue):
    """A task that raises is completed as failed, not left running."""
    queue.push_task("prove the thing")

    async def orchestrator(goal, worktree=None):
        raise RuntimeError("the work failed")

    async def scenario():
        pool = WorkerPool(n_workers=1)
        pool.boot()
        runner = asyncio.create_task(pool.run_workers(orchestrator_fn=orchestrator))
        for _ in range(100):
            await asyncio.sleep(0.1)
            row = queue.get_task_list()[0]
            if row[2] in ("failed", "success"):
                break
        pool.shutdown()
        await asyncio.wait_for(runner, timeout=30)

    asyncio.run(scenario())

    row = queue.get_task_list()[0]
    assert row[2] == "failed"

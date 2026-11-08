"""The creation-time worktree budget: a birth that would breach the floor is refused.

WHY THIS EXISTS. The full-disk rot was never a cleaning problem; it was a lifecycle
problem (idp#7801). A worktree is born for every task/lane/session, and removal was wired
to a different place than creation, so the worktrees at /private/tmp (~3.5GB) regenerated
faster than any sweep could archive them. bin/idp-disk-watch reaches the worktree tier
LAST and asks permission, so it can never close a regrowth loop the births keep feeding.

The only loop-closing point is creation. This test pins that a birth under the floor is
REFUSED, not created — the falsifier that proves the volume cannot regrow from worktrees.
"""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str, dotted: str):
    """Load a module of platform/ by path (platform/ has no __init__.py: idp#3564)."""
    if dotted in sys.modules:
        return sys.modules[dotted]
    spec = importlib.util.spec_from_file_location(dotted, str(REPO_ROOT / rel))
    module = importlib.util.module_from_spec(spec)
    sys.modules[dotted] = module
    spec.loader.exec_module(module)
    return module


wm = _load("platform/execution/worktree_manager.py", "platform.execution.worktree_manager")
WorktreeManager = wm.WorktreeManager
WorktreeManagerBudgetRefused = wm.WorktreeManagerBudgetRefused


@pytest.fixture
def manager(tmp_path):
    return WorktreeManager(base_path=str(tmp_path / "wt"), repo_root=str(tmp_path))


def test_a_birth_under_the_floor_is_refused_without_creating(manager, tmp_path, monkeypatch):
    """Free space under the floor refuses the worktree and leaves no path behind."""
    monkeypatch.setenv("WORKTREE_MIN_FREE_MB", "10")  # floor above the patched free space

    def fake_free(path):
        return 5  # 5M free, under the 10M floor

    monkeypatch.setattr(wm, "_free_mb", fake_free)

    with pytest.raises(WorktreeManagerBudgetRefused):
        manager.create_worktree(1)

    assert not (tmp_path / "wt").exists(), "a refused birth must not create the base dir"


def test_a_birth_above_the_floor_is_allowed(manager, tmp_path, monkeypatch):
    """Free space above the floor proceeds to a real worktree add."""
    monkeypatch.setattr(wm, "_free_mb", lambda path: 99999)

    # The manager will run `git worktree add`; the repo_root is a scratch dir that is not
    # a git repo, so the add fails with a RuntimeError — which proves the budget gate PASSED
    # (a refusal would have raised WorktreeManagerBudgetRefused instead).
    with pytest.raises(RuntimeError):
        manager.create_worktree(1)


def test_the_default_floor_matches_the_executor_floor():
    """The default creation floor is the executor's MIN_FREE_MB (1500), the estate's one line."""
    # The executor refuses to start a job below 1500M; the estate's one floor lives once.
    assert os.environ.get("WORKTREE_MIN_FREE_MB", "1500") == "1500"

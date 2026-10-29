#!/usr/bin/env python3
"""Worktree manager: spawn/cleanup isolated git worktrees per task.

Each task runs in its own worktree on its own branch.
Agents never collide with each other or the main branch.
"""

import os
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _queue_dispatcher():
    """The queue dispatcher, loaded the way platform/ has to be loaded.

    platform/ has no __init__.py (idp#3564): it collides with the stdlib `platform` module
    the moment anything imports it bare, and pytest itself imports `platform` at startup.
    So 'from platform.queue import dispatcher' raises ModuleNotFoundError ("'platform' is
    not a package"), and the sweep of orphaned worktrees caught that and did nothing at
    all: every worktree was skipped and the sweep reported zero.

    The queue package is loaded by file path and its own loader (platform/queue/__init__.py)
    does the seeding, so there is one implementation of the workaround rather than one per
    caller.
    """
    import importlib.util
    import os
    import sys

    if "platform.queue" not in sys.modules:
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        spec = importlib.util.spec_from_file_location(
            "platform.queue", os.path.join(root, "queue", "__init__.py")
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules["platform.queue"] = module
        spec.loader.exec_module(module)
    return sys.modules["platform.queue"].load_dispatcher()


class WorktreeManager:
    """
    Manages git worktrees for task isolation.
    One worktree per task, cleaned up after completion.
    """

    def __init__(self, base_path: str = None, repo_root: str = None):
        self.base_path = base_path or os.environ.get("WORKTREE_BASE", ".wt-agents")
        self.repo_root = repo_root or os.environ.get(
            "IDP_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        # The base directory is made when a worktree is made, not when the manager is
        # built: constructing a manager creates nothing in the working directory.

    def create_worktree(self, task_id: int) -> str:
        """
        Create a git worktree for a task.
        Returns: path to worktree
        """
        worktree_path = os.path.join(self.base_path, f"task-{task_id}")
        os.makedirs(self.base_path, exist_ok=True)

        try:
            # Add worktree on a detached HEAD
            result = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "git",
                    "worktree",
                    "add",
                    worktree_path,
                    "--detach",
                    "HEAD",
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to create worktree: {result.stderr}")

            logger.info(
                f"[WorktreeManager] Created worktree for task {task_id}: {worktree_path}"
            )
            return worktree_path

        except Exception as e:
            logger.error(
                f"[WorktreeManager] Failed to create worktree for task {task_id}: {e}"
            )
            raise

    def remove_worktree(self, task_id: int, force: bool = True) -> None:
        """
        Remove a git worktree, archiving what it holds first.

        The archive is what makes the removal safe: uncommitted changes and untracked
        files are kept in the estate's quarantine and the path is printed, so a removal is
        never a silent loss. An archive over the cap keeps the worktree: the work is
        worth more than the space.
        """
        worktree_path = os.path.join(self.base_path, f"task-{task_id}")

        try:
            dispatcher = _queue_dispatcher()
            archive = dispatcher.archive_worktree(worktree_path)
            if archive == "refused":
                logger.warning(
                    "[WorktreeManager] keeping %s: its leftovers are over the archive cap",
                    worktree_path,
                )
                return

            cmd = ["git", "worktree", "remove", worktree_path]
            if force:
                cmd.append("--force")

            result = subprocess.run(  # noqa: S603, S607
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                logger.warning(
                    f"[WorktreeManager] Failed to remove worktree {worktree_path}: {result.stderr}"
                )
            else:
                if archive:
                    logger.info(
                        "[WorktreeManager] Archived %s to %s", worktree_path, archive
                    )
                logger.info(f"[WorktreeManager] Removed worktree for task {task_id}")

        except Exception as e:
            logger.error(
                f"[WorktreeManager] Exception removing worktree {task_id}: {e}"
            )

    def sweep_orphaned(self) -> int:
        """
        Remove orphaned worktrees (tasks in terminal state or timeout).
        Returns: count of removed worktrees
        """
        from datetime import timedelta

        removed = 0

        try:
            dispatcher = _queue_dispatcher()
            worktrees = self._list_worktrees()

            for worktree_path in worktrees:
                # Extract task_id from path
                task_id_str = os.path.basename(worktree_path).replace("task-", "")
                try:
                    task_id = int(task_id_str)
                except ValueError:
                    continue

                # Check task status
                try:
                    task = dispatcher.load_task(task_id)
                    if not task:
                        # Task doesn't exist; orphaned
                        self.remove_worktree(task_id, force=True)
                        removed += 1
                        continue

                    # Check if task is terminal. The queue's terminal states are
                    # 'success' and 'failed' (the worker pool's own words); 'done' and
                    # 'dead_letter' are the older names and are still accepted.
                    if task.get("status") in (
                        "done",
                        "dead_letter",
                        "success",
                        "failed",
                    ):
                        self.remove_worktree(task_id, force=True)
                        removed += 1
                        continue

                    # Check if task is stuck (running > 2 hours)
                    updated_at = datetime.fromisoformat(
                        task.get("updated_at", datetime.now().isoformat())
                    )
                    if datetime.now() - updated_at > timedelta(hours=2):
                        self.remove_worktree(task_id, force=True)
                        removed += 1

                except Exception as e:
                    logger.warning(
                        f"[WorktreeManager] Error checking task {task_id}: {e}"
                    )

        except Exception as e:
            logger.error(f"[WorktreeManager] Sweep failed: {e}")

        if removed > 0:
            logger.info(f"[WorktreeManager] Swept {removed} orphaned worktrees")

        return removed

    def _list_worktrees(self) -> list[str]:
        """List all worktree paths."""
        try:
            result = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "git",
                    "worktree",
                    "list",
                    "--porcelain",
                ],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
            )

            worktrees = []
            for line in result.stdout.split("\n"):
                if line.startswith("worktree "):
                    path = line.split(" ", 1)[1]
                    if self.base_path in path:
                        worktrees.append(path)

            return worktrees

        except Exception as e:
            logger.error(f"[WorktreeManager] Failed to list worktrees: {e}")
            return []

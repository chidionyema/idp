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


class WorktreeManager:
    """
    Manages git worktrees for task isolation.
    One worktree per task, cleaned up after completion.
    """

    def __init__(self, base_path: str = None, repo_root: str = None):
        self.base_path = base_path or os.path.expanduser("~/dev/code/idp/.wt-agents")
        self.repo_root = repo_root or os.path.expanduser("~/dev/code/idp")
        os.makedirs(self.base_path, exist_ok=True)

    def create_worktree(self, task_id: int) -> str:
        """
        Create a git worktree for a task.
        Returns: path to worktree
        """
        worktree_path = os.path.join(self.base_path, f"task-{task_id}")

        try:
            # Add worktree on a detached HEAD
            result = subprocess.run(
                [  # noqa: S607
                    "git",
                    "worktree",
                    "add",
                    worktree_path,
                    "--detach",
                    "HEAD",
                ],  # noqa: S603
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
        Remove a git worktree.
        Force=True removes even if dirty.
        """
        worktree_path = os.path.join(self.base_path, f"task-{task_id}")

        try:
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
        from platform.queue import dispatcher
        from datetime import timedelta

        removed = 0

        try:
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

                    # Check if task is terminal
                    if task.get("status") in ("done", "dead_letter"):
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
            result = subprocess.run(
                [  # noqa: S607
                    "git",
                    "worktree",
                    "list",
                    "--porcelain",
                ],  # noqa: S603
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

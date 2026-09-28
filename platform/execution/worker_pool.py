#!/usr/bin/env python3
"""Worker pool: N-configurable, bounded to 10 initially.

Long-lived workers poll queue, claim tasks, execute in isolated worktrees.
Scales to arbitrary N; initial validation at N=10.
"""

import asyncio
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    N-configurable worker pool.
    Each worker: poll queue → claim task → execute in worktree → complete.
    """

    def __init__(
        self,
        n_workers: int = 10,
        max_workers: int = None,
    ):
        self.n_workers = min(n_workers, max_workers) if max_workers else n_workers
        self.max_workers = max_workers
        self.workers = {}
        self.active = False

    def boot(self):
        """Boot N workers."""
        logger.info(f"[WorkerPool] Booting {self.n_workers} workers...")

        for i in range(self.n_workers):
            worker_id = f"worker-{uuid.uuid4().hex[:4]}"
            self.workers[worker_id] = {
                "id": worker_id,
                "index": i + 1,
                "process": None,
                "started_at": datetime.now().isoformat(),
                "tasks_completed": 0,
                "last_task_id": None,
            }
            logger.info(f"  [{i + 1}/{self.n_workers}] {worker_id} ready")

        self.active = True

    def get_status(self) -> dict:
        """Report pool status."""
        return {
            "pool_size": self.n_workers,
            "max_workers": self.max_workers,
            "active_workers": len([w for w in self.workers.values() if w["process"]]),
            "total_tasks_completed": sum(
                w["tasks_completed"] for w in self.workers.values()
            ),
            "workers": self.workers,
        }

    def scale(self, new_n: int) -> None:
        """
        Scale pool to new_n workers.
        Graceful: existing workers finish current task before removal.
        """
        if self.max_workers and new_n > self.max_workers:
            logger.warning(
                f"[WorkerPool] Requested scale {new_n} exceeds max {self.max_workers}"
            )
            new_n = self.max_workers

        if new_n == self.n_workers:
            return

        if new_n > self.n_workers:
            # Scale up
            delta = new_n - self.n_workers
            logger.info(f"[WorkerPool] Scaling up +{delta} workers...")
            for _ in range(delta):
                worker_id = f"worker-{uuid.uuid4().hex[:4]}"
                self.workers[worker_id] = {
                    "id": worker_id,
                    "index": len(self.workers) + 1,
                    "process": None,
                    "started_at": datetime.now().isoformat(),
                    "tasks_completed": 0,
                    "last_task_id": None,
                }

        elif new_n < self.n_workers:
            # Scale down (graceful)
            delta = self.n_workers - new_n
            logger.info(
                f"[WorkerPool] Scaling down -{delta} workers (graceful, finish current tasks)"
            )
            # Mark excess workers for graceful shutdown
            excess = list(self.workers.values())[-delta:]
            for worker in excess:
                worker["graceful_shutdown"] = True

        self.n_workers = new_n

    async def run_workers(self, orchestrator_fn):
        """
        Run all workers until shutdown.
        Each worker is a long-lived coroutine.
        """
        if not self.active:
            self.boot()

        tasks = [
            asyncio.create_task(self._worker_loop(worker_id, orchestrator_fn))
            for worker_id in self.workers.keys()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _worker_loop(self, worker_id: str, orchestrator_fn) -> None:
        """
        Single worker loop.
        Poll queue → claim task → execute → complete → repeat.
        """
        from platform.queue import dispatcher

        worker_info = self.workers[worker_id]
        logger.info(f"[{worker_id}] Worker loop started")

        try:
            dispatcher.init_db()

            while self.active and not worker_info.get("graceful_shutdown"):
                # Sweep zombies once per cycle
                dispatcher.sweep_zombies()

                # Claim next task
                task = dispatcher.claim_task(worker_id)

                if not task:
                    # No task available; wait and retry
                    await asyncio.sleep(2)
                    continue

                task_id = task["id"]
                worker_info["last_task_id"] = task_id
                logger.info(
                    f"[{worker_id}] Claimed task {task_id}: {task['goal'][:60]}..."
                )

                try:
                    # Execute task in worktree
                    await orchestrator_fn(
                        goal=task["goal"],
                        worktree=task.get("worktree"),
                    )
                    dispatcher.complete_task(task_id, "success")
                    worker_info["tasks_completed"] += 1
                    logger.info(f"[{worker_id}] Task {task_id} complete")

                except Exception as e:
                    dispatcher.complete_task(task_id, "failed")
                    logger.error(
                        f"[{worker_id}] Task {task_id} failed: {e}",
                        exc_info=True,
                    )

                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"[{worker_id}] Worker loop crashed: {e}", exc_info=True)
        finally:
            logger.info(f"[{worker_id}] Worker loop stopped")

    def shutdown(self) -> None:
        """Signal shutdown. Workers finish current tasks."""
        logger.info("[WorkerPool] Shutdown signaled")
        self.active = False

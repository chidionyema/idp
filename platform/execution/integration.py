#!/usr/bin/env python3
"""End-to-end parallel agent execution at N=10 workers."""

import asyncio
import logging
from datetime import datetime

from platform.execution.worker_pool import WorkerPool
from platform.execution.worktree_manager import WorktreeManager
from platform.queue import dispatcher
from platform.orchestrator import run_orchestrator
from platform.eval.judge_worker import JudgeWorker
from platform.eval.pareval_layer import PartialEvalDecisionLayer
from platform.eval.comparison_policy import ComparisonPolicy
from platform.telemetry.span_retention_vacuum import VacuumJob
from platform.telemetry.span_outbox import OutboxPattern

logger = logging.getLogger(__name__)


class ParallelExecutionStack:
    """N-configurable parallel agent execution stack."""

    def __init__(self, n_workers: int = 10):
        self.n_workers = min(n_workers, 10)  # Bounded to 10
        self.pool = WorkerPool(n_workers=self.n_workers)
        self.worktree_mgr = WorktreeManager()
        self.judge = JudgeWorker()
        self.pareval = PartialEvalDecisionLayer(
            policy=ComparisonPolicy(
                min_confidence_threshold=0.70,
                max_unresolved_rate=0.10,
                bootstrap_samples=1000,
                coverage_requirement=1.0,
            )
        )
        self.vacuum_job = VacuumJob()
        self.outbox = OutboxPattern()
        self.started_at = None

    async def run(self) -> dict:
        """Run full parallel stack."""
        self.started_at = datetime.now()
        logger.info(f"[Stack] Starting with {self.n_workers} workers")

        # Initialize dispatcher
        dispatcher.init_db()
        self.worktree_mgr.sweep_orphaned()

        # Boot worker pool
        self.pool.boot()
        logger.info(f"[Stack] Booted {self.n_workers} workers")

        # Run all workers
        await self.pool.run_workers(orchestrator_fn=self._worker_orchestrator)

        # Post-execution cleanup
        self.worktree_mgr.sweep_orphaned()
        self.vacuum_job.execute_vacuum()
        self.outbox.process_outbox()

        elapsed = (datetime.now() - self.started_at).total_seconds()
        status = self.pool.get_status()

        return {
            "status": "complete",
            "workers": self.n_workers,
            "tasks_completed": status["total_tasks_completed"],
            "elapsed_seconds": elapsed,
            "pool_status": status,
        }

    async def _worker_orchestrator(self, goal: str, worktree: str = None) -> dict:
        """Orchestrator function for each worker."""
        result = await run_orchestrator(
            goal=goal,
            worktree=worktree,
        )

        # Judge the result
        if hasattr(result, "transcript") and result.transcript:
            verdict = self.judge.evaluate(result.transcript.transcript_id)
            result.judge_verdict = verdict

            # ParEval partial decision
            if hasattr(verdict, "judge_score"):
                self.pareval.observe(
                    task_id=result.transcript.task_id,
                    score_a=verdict.judge_score,
                    score_b=0.5,  # Baseline
                    stratum="general",
                )

        return result


async def main():
    """Run N=10 parallel execution stack."""
    stack = ParallelExecutionStack(n_workers=10)
    result = await stack.run()
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(main())
    print(f"Stack result: {result}")

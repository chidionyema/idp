"""The spine's worker: the Temporal side of the loop, on its own task queue.

Its own queue, deliberately. The sovereign worker owns the estate's agent sessions
(sovereign/engine/worker.py: SessionWorkflow); the spine's observer answers reconcile
events. Two queues, two workers, one Temporal: a workflow type nobody is serving is a
workflow that never runs, and one queue serving two unrelated workflows is a queue where
one of them can starve the other.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import emit_receipt, verify_reconciliation
from .workflow import ObserverWorkflow

LOG = logging.getLogger("spine.worker")

# The task queue the spine's workflows are served on.
TASK_QUEUE = os.environ.get("SPINE_TASK_QUEUE", "spine")
# The namespace the estate's Temporal runs (platform/temporal/temporal.yaml: estate).
NAMESPACE = os.environ.get("TEMPORAL_NAMESPACE", "estate")
# The frontend's in-cluster address (platform/temporal/worker.yaml).
ADDRESS = os.environ.get("TEMPORAL_ADDRESS", "temporal-frontend.temporal.svc:7233")


async def run_worker(
    address: str = ADDRESS, namespace: str = NAMESPACE, task_queue: str = TASK_QUEUE
) -> None:
    """Serve the observer workflow until the pod is asked to stop."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    client = await Client.connect(address, namespace=namespace)
    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[ObserverWorkflow],
        activities=[verify_reconciliation, emit_receipt],
    )
    LOG.info(
        "spine worker starting: address=%s namespace=%s task_queue=%s",
        address,
        namespace,
        task_queue,
    )
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover - not unix
            pass
    async with worker:
        # The readiness file is written only while the worker is polling, so the probe
        # answers "is somebody serving the spine's workflows", not "is the process alive".
        # The same shape platform/temporal/worker.yaml uses for the sovereign worker.
        ready = "/tmp/worker.ready"  # noqa: S108 - pod-local marker, as platform/temporal/worker.yaml
        try:
            with open(ready, "w", encoding="utf-8") as handle:
                handle.write("ready\n")
        except OSError as exc:  # pragma: no cover - a read-only /tmp is a broken pod
            LOG.warning("could not write the ready file %s: %s", ready, exc)
        await stop.wait()
    try:
        os.unlink(ready)
    except OSError:
        pass
    LOG.info("spine worker stopping")


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":  # pragma: no cover - module entry
    main()

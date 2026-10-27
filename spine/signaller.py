"""The Temporal half of the bridge: one signal, one workflow.

The Temporal client here is the estate's: temporalio, the same pin the sovereign worker
runs (sovereign/requirements.txt: temporalio==1.32.0). The build kit proposed a Go client;
the estate's Temporal plane is Python, the sovereign SessionWorkflow is Python, and a second
client stack for one bridge would be a second thing to keep alive. The logic the build kit
describes is ported line for line -- the decision table, not the language.

The signal is idempotent at Temporal: the same workflow id and the same signal name twice is
two signals, and the workflow reads the event id in the payload and ignores the one it has
already seen. The bridge's dedup store is the first line; the workflow's own check is the
second, because a crash between the signal and the dedup write is exactly the case the
build kit names.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from temporalio.client import Client

LOG = logging.getLogger("spine.signaller")

# The namespace the estate's Temporal runs (platform/temporal/temporal.yaml: estate).
DEFAULT_NAMESPACE = "estate"


class TemporalSignaller:
    """Signals a workflow by id. Nothing else about the workflow is known here."""

    def __init__(self, client: Client, namespace: str = DEFAULT_NAMESPACE) -> None:
        self._client = client
        self._namespace = namespace

    @classmethod
    async def connect(
        cls,
        address: str,
        namespace: str = DEFAULT_NAMESPACE,
    ) -> "TemporalSignaller":
        client = await Client.connect(address, namespace=namespace)
        return cls(client, namespace=namespace)

    async def signal(
        self, workflow_id: str, signal_name: str, payload: Dict[str, Any]
    ) -> None:
        await self._client.signal_workflow(
            workflow_id,
            signal_name=signal_name,
            arg=payload,
            namespace=self._namespace,
        )
        LOG.info("signalled %s on %s", workflow_id, signal_name)


async def connect(
    address: str, namespace: str = DEFAULT_NAMESPACE
) -> TemporalSignaller:
    return await TemporalSignaller.connect(address, namespace=namespace)

"""Typed DAG execution on the existing sovereign Temporal task queue.

Execution authority is Temporal. The reactor and founder surface are projections.
No network, file or shell access is performed inside deterministic workflow code.
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from sovereign.automation.contracts import verify_plan


@workflow.defn(name="EstateAutomationWorkflowV1")
class EstateAutomationWorkflowV1:
    def __init__(self) -> None:
        self._state: dict[str, Any] = {"status": "initialising", "steps": {}}
        self._approved: set[str] = set()
        self._denied: set[str] = set()

    @workflow.query
    def state(self) -> dict[str, Any]:
        return self._state

    @workflow.signal
    def approve(self, gate: str) -> None:
        # The gateway must verify a signed, authorized caller before signalling.
        self._approved.add(gate)

    @workflow.signal
    def deny(self, gate: str) -> None:
        self._denied.add(gate)

    async def _receipt(self, kind: str, text: str) -> None:
        record = {
            "session_id": self._state["workflow_id"], "kind": "automation-" + kind,
            "by": "automation-kernel", "text": text,
            "run_id": self._state["run_id"], "plan_hash": self._state["plan_hash"],
            "source_sha": self._state["release"]["source_sha"],
            "artifact_digest": self._state["release"]["artifact_digest"],
            "config_digest": self._state["release"]["config_digest"],
            "status": self._state["status"], "steps": self._state["steps"],
        }
        await workflow.execute_activity(
            "append_receipt", record, start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

    async def _step(self, node: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
        name = node["id"]
        self._state["steps"][name] = {"state": "running", "started_at": workflow.now().isoformat()}
        self._state["updated_at"] = workflow.now().isoformat()
        try:
            result = await workflow.execute_activity(
                "automation_activity",
                {"action": node["action"], "inputs": node["inputs"],
                 "dependencies": {d: results[d] for d in node["deps"]},
                 "workflow_id": self._state["workflow_id"],
                 "plan_hash": self._state["plan_hash"],
                 "run_id": self._state["run_id"],
                 "source_sha": self._state["release"]["source_sha"],
                 "release": self._state["release"], "node_id": name},
                start_to_close_timeout=timedelta(seconds=node["timeout_s"]),
                heartbeat_timeout=timedelta(seconds=min(30, node["timeout_s"])),
                retry_policy=RetryPolicy(maximum_attempts=node["max_attempts"]),
            )
            self._state["steps"][name] = {"state": "verified", "evidence": result,
                                          "ended_at": workflow.now().isoformat()}
            self._state["updated_at"] = workflow.now().isoformat()
            return result
        except Exception as exc:
            self._state["steps"][name] = {"state": "failed", "failure_type": type(exc).__name__,
                                          "ended_at": workflow.now().isoformat()}
            self._state["updated_at"] = workflow.now().isoformat()
            raise

    @workflow.run
    async def run(self, plan: dict[str, Any]) -> dict[str, Any]:
        verify_plan(plan)
        info = workflow.info()
        self._state = {
            "workflow_id": info.workflow_id, "run_id": info.run_id,
            "plan_hash": plan["plan_hash"], "release": dict(plan["release"]),
            "contract": dict(plan["contract"]), "status": "running", "steps": {},
            "updated_at": workflow.now().isoformat(),
        }
        await self._receipt("started", "compiled plan accepted")
        results: dict[str, Any] = {}
        pending = {n["id"]: n for n in plan["steps"]}
        try:
            while pending:
                ready = sorted(
                    (n for n in pending.values() if set(n["deps"]) <= set(results)),
                    key=lambda n: n["id"],
                )
                if not ready:
                    raise ValueError("unresolved DAG dependency")
                batch = ready[:plan["max_concurrency"]]
                for node in batch:
                    if node["approval"]:
                        gate = node["id"]
                        self._state["status"] = "waiting-approval"
                        await workflow.wait_condition(lambda: gate in self._approved or gate in self._denied)
                        if gate in self._denied:
                            self._state["status"] = "denied"
                            await self._receipt("denied", gate)
                            return self._state
                        self._state["status"] = "running"
                outcomes = await asyncio.gather(
                    *(self._step(n, results) for n in batch), return_exceptions=True,
                )
                errors = [v for v in outcomes if isinstance(v, BaseException)]
                if errors:
                    raise errors[0]
                for node, result in zip(batch, outcomes):
                    results[node["id"]] = result
                    del pending[node["id"]]
            self._state["status"] = "verified"
            await self._receipt("verified", "independent probe set satisfied")
        except Exception as exc:
            self._state["status"] = "failed"
            self._state["failure_type"] = type(exc).__name__
            self._state["rollback"] = "not-supported-candidate-only"
            await self._receipt("failed", self._state["failure_type"])
        return self._state

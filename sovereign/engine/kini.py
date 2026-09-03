"""KiniFinishWorkflow (crew#396 step 3): "type 'Finish KINI', close the laptop, wake up to a
green dashboard".

One activity per KINI checkpoint (crew#284 CP1-CP7). Each runs the bdd files bound to that
checkpoint and returns one of four verdicts:

  pass            pytest exit 0
  fail            pytest exit 1: the checkpoint's own assertions failed; retrying will not help
  unbound         no bdd file is bound to the checkpoint yet, or a bound file is missing
  platform-fault  pytest could not run to a verdict (usage/internal error, import error,
                  timeout): the platform under the test is what broke

Every activity carries a RetryPolicy. A platform-fault result is not retried blindly: the
workflow calls the heal activity (the in-cluster equivalent of bin/idp-cluster-state, read
through the Kubernetes API on the worker's ServiceAccount), waits, and re-runs the checkpoint,
up to heal_max_rounds. That is the crew#268 playbook's "zombie/drift" branch as code.

Like sovereign/engine/workflow.py this module's workflow imports nothing from sovereign.config:
the trigger (sovereign.cli `kini finish`, or the board word FINISH: KINI) hands it
config.kini_workflow_params(). Activities do read config; they run outside the sandbox."""
from __future__ import annotations

import asyncio
import json
import os
import ssl
import sys
import urllib.request
from datetime import timedelta
from pathlib import Path
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

RUN_CHECKPOINT = "kini_run_checkpoint"
CLUSTER_READY = "kini_cluster_ready"
WORKFLOW = "KiniFinishWorkflow"

PASS = "pass"
FAIL = "fail"
UNBOUND = "unbound"
PLATFORM_FAULT = "platform-fault"


@workflow.defn(name=WORKFLOW)
class KiniFinishWorkflow:
    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        self._results: dict[str, Any] = {}
        cp_retry = RetryPolicy(maximum_attempts=int(params["cp_attempts"]))
        heal_retry = RetryPolicy(maximum_attempts=int(params["heal_attempts"]))
        for cp in params["checkpoints"]:
            rounds = 0
            heal: dict[str, Any] | None = None
            while True:
                result = await workflow.execute_activity(
                    RUN_CHECKPOINT,
                    {"cp": cp},
                    start_to_close_timeout=timedelta(seconds=int(params["cp_timeout_s"])),
                    heartbeat_timeout=timedelta(seconds=int(params["heartbeat_timeout_s"])),
                    retry_policy=cp_retry,
                )
                result = dict(result)
                result["heal_rounds"] = rounds
                if heal is not None:
                    result["heal"] = heal
                if result["verdict"] != PLATFORM_FAULT or rounds >= int(params["heal_max_rounds"]):
                    break
                rounds += 1
                heal = await workflow.execute_activity(
                    CLUSTER_READY,
                    {"cp": cp, "round": rounds, "detail": result.get("detail")},
                    start_to_close_timeout=timedelta(seconds=int(params["heal_timeout_s"])),
                    heartbeat_timeout=timedelta(seconds=int(params["heartbeat_timeout_s"])),
                    retry_policy=heal_retry,
                )
                if not heal.get("ready"):
                    await workflow.sleep(timedelta(seconds=int(params["heal_poll_s"])))
            self._results[str(cp)] = result
        verdicts = {k: v["verdict"] for k, v in self._results.items()}
        return {
            "ok": all(v == PASS for v in verdicts.values()),
            "green": [k for k, v in verdicts.items() if v == PASS],
            "red": [k for k, v in verdicts.items() if v != PASS],
            "checkpoints": self._results,
        }

    @workflow.query
    def progress(self) -> dict[str, Any]:
        return {k: v["verdict"] for k, v in getattr(self, "_results", {}).items()}


def classify(returncode: int | None, exit_no_tests: int, timed_out: bool = False) -> str:
    """Rung 2 material: total over every int, never silent on the unknown branch."""
    if timed_out or returncode is None:
        return PLATFORM_FAULT
    if returncode == 0:
        return PASS
    if returncode == 1:
        return FAIL
    if returncode == exit_no_tests:
        return UNBOUND
    return PLATFORM_FAULT


async def _run_pytest(paths: list[str], cwd: Path, args: list[str], timeout_s: int, heartbeat_s: int, tail: int) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "pytest", *args, *paths,
        cwd=str(cwd), stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
    )
    out_task = asyncio.ensure_future(proc.stdout.read()) if proc.stdout else None
    waited = 0
    timed_out = False
    while True:
        try:
            await asyncio.wait_for(asyncio.shield(proc.wait()), timeout=heartbeat_s)
            break
        except asyncio.TimeoutError:
            waited += heartbeat_s
            if activity.in_activity():
                activity.heartbeat({"paths": paths, "waited_s": waited})
            if waited >= timeout_s:
                timed_out = True
                proc.kill()
                await proc.wait()
                break
    raw = (await out_task) if out_task else b""
    lines = raw.decode(errors="replace").splitlines()
    return {"returncode": proc.returncode, "timed_out": timed_out, "output": lines[-tail:]}


@activity.defn(name=RUN_CHECKPOINT)
async def run_checkpoint(inp: dict[str, Any]) -> dict[str, Any]:
    """Runs one checkpoint's bound bdd files. `inp` may override `tests` (list of paths) and
    `cwd`; the defaults come from config (kini.cp<n>_tests, kini.sovereign_dir)."""
    from sovereign import config

    cp = int(inp["cp"])
    cwd = Path(inp.get("cwd") or config.KINI_SOVEREIGN_DIR)
    paths = list(inp.get("tests") if inp.get("tests") is not None else config.KINI_CP_TESTS.get(cp, []))
    if not paths:
        return {"cp": cp, "verdict": UNBOUND, "detail": "no bdd file bound", "tests": []}
    missing = [p for p in paths if not (cwd / p).exists()]
    if missing:
        return {"cp": cp, "verdict": UNBOUND, "detail": f"bound file missing: {missing}", "tests": paths}
    run = await _run_pytest(
        paths, cwd, list(config.KINI_PYTEST_ARGS),
        int(inp.get("timeout_s") or config.KINI_CP_TIMEOUT_S),
        int(inp.get("heartbeat_s") or config.KINI_CP_HEARTBEAT_S),
        config.KINI_OUTPUT_TAIL_LINES,
    )
    verdict = classify(run["returncode"], config.KINI_PYTEST_EXIT_NO_TESTS, run["timed_out"])
    return {
        "cp": cp, "verdict": verdict, "tests": paths, "returncode": run["returncode"],
        "timed_out": run["timed_out"], "detail": run["output"][-1] if run["output"] else "",
        "output": run["output"],
    }


def _in_cluster() -> bool:
    from sovereign import config

    return bool(os.environ.get(config.KINI_K8S_HOST_ENV)) and config.KINI_K8S_TOKEN_FILE.exists()


def _nodes_ready() -> dict[str, Any]:
    """The same question bin/idp-cluster-state answers from the receipt, asked of the API
    directly because the worker is inside the cluster and has no OCI identity."""
    from sovereign import config

    host = os.environ[config.KINI_K8S_HOST_ENV]
    port = os.environ[config.KINI_K8S_PORT_ENV]
    token = config.KINI_K8S_TOKEN_FILE.read_text().strip()
    ctx = ssl.create_default_context(cafile=str(config.KINI_K8S_CA_FILE))
    req = urllib.request.Request(
        f"https://{host}:{port}{config.KINI_K8S_NODES_PATH}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=config.KINI_K8S_REQUEST_TIMEOUT_S, context=ctx) as resp:
        body = json.loads(resp.read())
    items = body.get("items", [])
    ready = [
        n for n in items
        if any(c.get("type") == "Ready" and c.get("status") == "True" for c in n["status"].get("conditions", []))
    ]
    return {"nodes": len(items), "ready_nodes": len(ready), "ready": bool(items) and len(ready) == len(items)}


@activity.defn(name=CLUSTER_READY)
async def cluster_ready(inp: dict[str, Any]) -> dict[str, Any]:
    """The heal step. In the cluster: poll the node list until every node is Ready or the
    activity's own timeout ends it (Temporal retries per the policy). Outside the cluster
    there is nothing to read, so the answer is BLIND (never a verdict) and the workflow
    simply waits heal_poll_s before the re-run."""
    from sovereign import config

    if not _in_cluster():
        return {"ready": None, "blind": True, "reason": "not in a pod, so no Kubernetes API"}
    waited = 0
    while True:
        state = await asyncio.to_thread(_nodes_ready)
        if state["ready"]:
            return {**state, "blind": False, "waited_s": waited}
        activity.heartbeat({**state, "waited_s": waited})
        await asyncio.sleep(config.KINI_HEAL_POLL_S)
        waited += config.KINI_HEAL_POLL_S
        if waited >= config.KINI_HEAL_TIMEOUT_S:
            return {**state, "blind": False, "waited_s": waited}


WORKFLOWS = [KiniFinishWorkflow]
ACTIVITIES = [run_checkpoint, cluster_ready]

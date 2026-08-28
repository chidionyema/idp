"""Binds features/sovereign-bus/cp0c_kini_finish_workflow.feature (crew#396 step 3).
Rung 2 (classify over real pytest exits) and rung 4 (the retry and heal paths on a local
Temporal, skipped where the `temporal` CLI is absent)."""
from __future__ import annotations

import asyncio
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when
from temporalio import activity
from temporalio.client import Client
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from sovereign import config
from sovereign.engine import kini, worker
from sovereign.shadow import config_keys as ck

IDP = Path(__file__).resolve().parents[3]
scenarios("features/sovereign-bus/cp0c_kini_finish_workflow.feature")


@pytest.fixture
def state() -> dict:
    return {"calls": {}}


def _run(inp: dict) -> dict:
    return asyncio.run(kini.run_checkpoint(inp))


def _bound(tmp_path: Path, name: str, body: str, conftest: str | None = None) -> dict:
    d = tmp_path / name
    d.mkdir()
    (d / f"test_{name}.py").write_text(textwrap.dedent(body))
    if conftest is not None:
        (d / "conftest.py").write_text(conftest)
    return {"cp": 1, "cwd": str(tmp_path), "tests": [f"{name}/test_{name}.py"]}


@given("a checkpoint bound to a passing bdd file")
def _passing(state: dict, tmp_path: Path) -> None:
    state["inp"] = _bound(tmp_path, "green", "def test_green():\n    assert True\n")


@given("a checkpoint bound to a failing bdd file")
def _failing(state: dict, tmp_path: Path) -> None:
    state["inp"] = _bound(tmp_path, "red", "def test_red():\n    assert False\n")


@given("a checkpoint bound to no bdd file")
def _unbound(state: dict, tmp_path: Path) -> None:
    state["inp"] = {"cp": 4, "cwd": str(tmp_path), "tests": []}


@given("a checkpoint whose conftest cannot import")
def _fault(state: dict, tmp_path: Path) -> None:
    state["inp"] = _bound(
        tmp_path, "fault", "def test_x():\n    assert True\n", conftest="raise RuntimeError('platform gone')\n"
    )


@then("the checkpoint activity returns pass")
def _is_pass(state: dict) -> None:
    assert _run(state["inp"])["verdict"] == kini.PASS


@then("the checkpoint activity returns fail")
def _is_fail(state: dict) -> None:
    assert _run(state["inp"])["verdict"] == kini.FAIL


@then("the checkpoint activity returns unbound")
def _is_unbound(state: dict) -> None:
    assert _run(state["inp"])["verdict"] == kini.UNBOUND
    missing = _run({"cp": 4, "cwd": state["inp"]["cwd"], "tests": ["nope/test_nope.py"]})
    assert missing["verdict"] == kini.UNBOUND, missing


@then("the checkpoint activity returns platform-fault")
def _is_fault(state: dict) -> None:
    r = _run(state["inp"])
    assert r["verdict"] == kini.PLATFORM_FAULT, r
    assert kini.classify(None, config.KINI_PYTEST_EXIT_NO_TESTS) == kini.PLATFORM_FAULT
    assert kini.classify(0, config.KINI_PYTEST_EXIT_NO_TESTS, timed_out=True) == kini.PLATFORM_FAULT


# --- the retry and heal paths on a local Temporal -------------------------------------------

@given("a worker on a local Temporal with a checkpoint that fails once and then passes")
def _flaky(state: dict) -> None:
    if not shutil.which(str(ck.get("temporal.cli_binary"))):
        pytest.skip("temporal CLI not on PATH")
    calls = state["calls"]

    @activity.defn(name=kini.RUN_CHECKPOINT)
    async def fake_run(inp: dict) -> dict:
        cp = inp["cp"]
        calls[cp] = calls.get(cp, 0) + 1
        if cp == 1 and calls[cp] == 1:
            raise ApplicationError("flake: the activity itself blew up")
        if cp == 2 and calls[cp] == 1:
            return {"cp": cp, "verdict": kini.PLATFORM_FAULT, "detail": "temporal-frontend unreachable"}
        return {"cp": cp, "verdict": kini.PASS}

    @activity.defn(name=kini.CLUSTER_READY)
    async def fake_heal(inp: dict) -> dict:
        calls["heal"] = calls.get("heal", 0) + 1
        return {"ready": True, "blind": False, "nodes": 1, "ready_nodes": 1}

    state["activities"] = [fake_run, fake_heal]


@given("a checkpoint that reports a platform fault once and then passes")
def _faulting(state: dict) -> None:
    state["params"] = {**config.kini_workflow_params(), "checkpoints": [1, 2, 3], "heal_poll_s": 0}


@when("KiniFinishWorkflow runs")
def _runs(state: dict) -> None:
    async def go() -> dict:
        cli = shutil.which(str(ck.get("temporal.cli_binary")))
        env = await WorkflowEnvironment.start_local(dev_server_existing_path=cli)
        try:
            async with Worker(env.client, task_queue="kini-test", workflows=kini.WORKFLOWS, activities=state["activities"]):
                return await env.client.execute_workflow(
                    kini.WORKFLOW, state["params"], id="kini-test-run", task_queue="kini-test"
                )
        finally:
            await env.shutdown()

    state["result"] = asyncio.run(go())


@then("every checkpoint is green")
def _green(state: dict) -> None:
    r = state["result"]
    assert r["ok"] and r["red"] == [] and r["green"] == ["1", "2", "3"], r


@then("the flaky checkpoint ran twice under its RetryPolicy")
def _retried(state: dict) -> None:
    assert state["calls"][1] == 2, state["calls"]
    assert state["result"]["checkpoints"]["1"]["heal_rounds"] == 0


@then("the faulting checkpoint healed once and ran twice")
def _healed(state: dict) -> None:
    assert state["calls"][2] == 2 and state["calls"]["heal"] == 1, state["calls"]
    cp2 = state["result"]["checkpoints"]["2"]
    assert cp2["heal_rounds"] == 1 and cp2["heal"]["ready"] is True, cp2


# --- registration and the trigger ----------------------------------------------------------

@then("sovereign.engine.worker registers KiniFinishWorkflow, kini_run_checkpoint and kini_cluster_ready")
def _registered() -> None:
    assert kini.KiniFinishWorkflow in worker.WORKFLOWS
    names = {a.__temporal_activity_definition.name for a in worker.ACTIVITIES}
    assert {kini.RUN_CHECKPOINT, kini.CLUSTER_READY} <= names, names


@then("bin/idp-kini finish starts it by the one workflow id in config")
def _cli() -> None:
    assert (IDP / "bin/idp-kini").stat().st_mode & 0o111
    src = (IDP / "sovereign/cli.py").read_text()
    assert "id=config.KINI_WORKFLOW_ID" in src and "kini.WORKFLOW" in src
    r = subprocess.run([str(IDP / "bin/idp-kini"), "finish", "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and "--wait" in r.stdout, r.stderr


@then("the worker Deployment can read nodes through its own ServiceAccount")
def _rbac() -> None:
    r = subprocess.run(["kubectl", "kustomize", str(IDP / "platform/temporal")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    docs = [d for d in yaml.safe_load_all(r.stdout) if d]
    dep = next(d for d in docs if d["kind"] == "Deployment" and d["metadata"]["name"] == "sovereign-worker")
    sa = dep["spec"]["template"]["spec"]["serviceAccountName"]
    assert any(d["kind"] == "ServiceAccount" and d["metadata"]["name"] == sa for d in docs), sa
    role = next(d for d in docs if d["kind"] == "ClusterRole" and d["metadata"]["name"] == "sovereign-worker-nodes")
    assert any("nodes" in rule["resources"] and {"get", "list"} <= set(rule["verbs"]) for rule in role["rules"]), role
    crb = next(d for d in docs if d["kind"] == "ClusterRoleBinding" and d["metadata"]["name"] == "sovereign-worker-nodes")
    assert crb["roleRef"]["name"] == "sovereign-worker-nodes"
    assert any(s["kind"] == "ServiceAccount" and s["name"] == sa and s["namespace"] == "temporal" for s in crb["subjects"]), crb


@then("the worker image carries pytest-bdd and features/ so a checkpoint can run there")
def _image() -> None:
    df = [l.strip() for l in (IDP / "sovereign-worker.Dockerfile").read_text().splitlines() if l.strip() and not l.startswith("#")]
    assert any(l.startswith("RUN ") and "requirements-dev.txt" in l for l in df), df
    assert "COPY features /app/features" in df and "COPY sovereign /app/sovereign" in df, df
    assert "pytest-bdd" in (IDP / "sovereign/requirements-dev.txt").read_text()

"""Binds features/drills/chaos-drill.feature (crew#292 CP4, crew#297). The receipt container from
platform/chaos/backstage-pod-kill.yaml is judged as a Pod by the Kyverno CLI against the pinned
policy set, once owned by a WorkflowNode and once by a ReplicaSet. The helpers are the ones
tests/test_incident_chaos_task_pod_admitted.py proves, loaded from that file."""
import importlib.util
import shutil
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

scenarios("features/drills/chaos-drill.feature")

IDP = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("incident_task_pod", IDP / "tests/test_incident_chaos_task_pod_admitted.py")
incident = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(incident)


@pytest.fixture
def state() -> dict:
    return {}


@given("the receipt container spec from platform/chaos/backstage-pod-kill.yaml as a Pod")
def _pod(state: dict) -> None:
    for tool in ("kyverno", "kubectl"):
        assert shutil.which(tool), f"{tool} is not installed; the bdd job installs it"
    container, _ = incident._task_container()
    assert container.get("image") and container.get("command"), container


@when("Kyverno judges it owned by a WorkflowNode")
def _judge_workflow(state: dict, tmp_path: Path) -> None:
    (tmp_path / "w").mkdir(exist_ok=True)
    state["workflow"] = incident._judge(incident._pod("WorkflowNode"), tmp_path / "w")


@then("it is admitted")
def _admitted(state: dict) -> None:
    out = state["workflow"]
    assert "fail: 0" in out and "error: 0" in out, out


@when("Kyverno judges the same Pod owned by a ReplicaSet")
def _judge_rs(state: dict, tmp_path: Path) -> None:
    (tmp_path / "r").mkdir(exist_ok=True)
    state["replicaset"] = incident._judge(incident._pod("ReplicaSet"), tmp_path / "r")


@then("require-pod-probes refuses it")
def _refused(state: dict) -> None:
    out = state["replicaset"]
    assert "require-pod-probes" in out and "fail" in out.lower(), out

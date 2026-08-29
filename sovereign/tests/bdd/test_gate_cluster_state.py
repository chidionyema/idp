"""Binds features/drills/cluster-state.feature (crew#345). Scenario 1 judges the CronJob's pod
with the Kyverno CLI against the pinned policy set (helpers from
tests/test_incident_chaos_task_pod_admitted.py). Scenarios 2-4 run bin/idp-cluster-state against a
fake `oci` on PATH that answers head/get from a fixture, so the grader is proved both ways
(LAW 45 step 3) without a bucket."""
import importlib.util
import json
import os
import shutil
import stat
import subprocess
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

scenarios("features/drills/cluster-state.feature")

IDP = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("incident_task_pod", IDP / "tests/test_incident_chaos_task_pod_admitted.py")
incident = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(incident)


def cronjob_container() -> tuple[dict, list]:
    docs = list(yaml.safe_load_all(open(IDP / "platform/state/cluster-state.yaml")))
    cj = next(d for d in docs if d and d.get("kind") == "CronJob")
    spec = cj["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    return spec["containers"][0], spec.get("volumes", [])


def pod(owner_kind: str) -> dict:
    c, vols = cronjob_container()
    return {
        "apiVersion": "v1", "kind": "Pod",
        "metadata": {"name": "cluster-state", "namespace": "backstage",
                     "ownerReferences": [{"apiVersion": "batch/v1", "kind": owner_kind, "name": "cluster-state", "uid": "0"}]},
        "spec": {"restartPolicy": "Never", "containers": [c], "volumes": vols},
    }


@pytest.fixture
def state() -> dict:
    return {}


@given("the receipt container spec from platform/state/cluster-state.yaml as a Pod")
def _pod(state: dict) -> None:
    for tool in ("kyverno", "kubectl"):
        assert shutil.which(tool), f"{tool} is not installed; the bdd job installs it"
    c, _ = cronjob_container()
    assert c.get("image") and c.get("command"), c


@when("Kyverno judges it owned by a Job")
def _judge_job(state: dict, tmp_path: Path) -> None:
    (tmp_path / "j").mkdir(exist_ok=True)
    state["job"] = incident._judge(pod("Job"), tmp_path / "j")


@then("it is admitted")
def _admitted(state: dict) -> None:
    out = state["job"]
    assert "fail: 0" in out.replace(",", "").lower() or "0 failed" in out.lower(), out


@when("Kyverno judges the same Pod owned by a ReplicaSet")
def _judge_rs(state: dict, tmp_path: Path) -> None:
    (tmp_path / "r").mkdir(exist_ok=True)
    state["rs"] = incident._judge(pod("ReplicaSet"), tmp_path / "r")


@then("require-pod-probes refuses it")
def _refused(state: dict) -> None:
    out = state["rs"]
    assert "require-pod-probes" in out and "fail" in out.lower(), out


@given(parsers.parse('a receipt "{line}" written {minutes:d} minutes ago'))
def _receipt(state: dict, tmp_path: Path, line: str, minutes: int) -> None:
    when_ = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    # crew#583 CP2: the row reads the store's own clock (`date`) beside the stamp, never this Mac's
    (tmp_path / "head.json").write_text(json.dumps({"last-modified": format_datetime(when_),
                                                    "date": format_datetime(datetime.now(timezone.utc))}))
    (tmp_path / "body.txt").write_text(line + "\n" + json.dumps({"nodes": []}) + "\n")
    fake = tmp_path / "bin" / "oci"
    fake.parent.mkdir()
    fake.write_text(f"""#!/bin/sh
case "$*" in
  *"object head"*) cat {tmp_path}/head.json ;;
  *"object get"*) cat {tmp_path}/body.txt ;;
  *) echo "unexpected: $*" >&2; exit 9 ;;
esac
""")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
    state["path"] = f"{fake.parent}:{os.environ['PATH']}"


@when("bin/idp-cluster-state grades it")
def _grade(state: dict) -> None:
    r = subprocess.run([str(IDP / "bin/idp-cluster-state")], capture_output=True, text=True,
                       env={**os.environ, "PATH": state["path"]})
    state["verdict"] = r.stdout.strip().splitlines()[0] if r.stdout.strip() else r.stderr
    state["rc"] = r.returncode


@then(parsers.parse('the verdict line starts with "{prefix}"'))
def _starts(state: dict, prefix: str) -> None:
    assert state["verdict"].startswith(prefix), (state["verdict"], state["rc"])
    assert state["rc"] == (0 if prefix.startswith("ok") else 1), state


@then(parsers.parse('the verdict line starts with "{prefix}" and names {token}'))
def _starts_names(state: dict, prefix: str, token: str) -> None:
    assert state["verdict"].startswith(prefix), (state["verdict"], state["rc"])
    assert state["rc"] == 1, state
    needle = "min old" if token == "the age" else token
    assert needle in state["verdict"], state["verdict"]

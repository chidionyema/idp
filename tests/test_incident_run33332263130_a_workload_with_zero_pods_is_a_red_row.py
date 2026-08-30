"""run 33332263130 / founder 2026-08-30 "did I not say everything must be transparent":
Deployment healing/estate (k8sgpt) held ZERO pods for a day while every page read green.
Kyverno denied each ReplicaSet pod at admission, so the pods list never saw a pod (none
were created), the Flux rows were Ready (the Deployment object applied fine), and only
DaemonSets had a short row (crew#320). Rule, crew#320 extended: the receipt carries every
Deployment and StatefulSet short of its desired replicas, and the grader fails the row and
prints the Warning events that name it. spec.replicas 0 is a scale-down, not short."""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"
GRADER = ROOT / "bin/idp-cluster-state"


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]


def _grader_py():
    text = GRADER.read_text()
    return text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]


def _grade(receipt: str):
    head = json.dumps(
        {
            "last-modified": format_datetime(
                datetime.now(timezone.utc) - timedelta(minutes=1)
            ),
            "date": format_datetime(datetime.now(timezone.utc)),
        }
    )
    r = subprocess.run(
        [sys.executable, "-c", _grader_py(), head, receipt, "60", "--json"],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "IDP_LIB": str(ROOT / "bin" / "lib")},
    )
    return r.returncode, r.stdout


def _receipt(deploy_short: list, with_count: bool = True) -> str:
    head = (
        "ok cluster-state at 2026-08-30T20:00:00Z nodes=1 ready=1 pods=45 pods_not_ready=0"
        " flux=20 flux_not_ready=0 ds=3 ds_short=0"
    )
    if with_count:
        head += f" deploy_short={len(deploy_short)}"
    head += (
        " events_warning=1 monitoring_rules=1 alert_watchdog=1"
        " cpu_used_pct=30 mem_used_pct=25 cpu_req_pct=12 mem_req_pct=4"
    )
    events = [
        {
            "at": "2026-08-30T19:53:33",
            "ns": "healing",
            "kind": "ReplicaSet",
            "name": "estate-68cbf5bf6",
            "reason": "FailedCreate",
            "count": 4,
            "message": 'admission webhook "validate.kyverno.svc-fail" denied the request: require-pod-probes: validate-probes',
        }
    ]
    return (
        head
        + "\n"
        + json.dumps(
            {
                "flux_not_ready": [],
                "ds_short": [],
                "deploy_short": deploy_short,
                "events_warning": events,
            }
        )
    )


def test_collector_lists_deployments_and_statefulsets_and_the_role_can_read_them():
    docs = _docs()
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    compile(collect, "collect.py", "exec")
    assert '"/apis/apps/v1/deployments"' in collect
    assert '"/apis/apps/v1/statefulsets"' in collect
    assert "deploy_short=" in collect
    role = next(d for d in docs if d["kind"] == "ClusterRole")
    granted = {
        (g, r)
        for rule in role["rules"]
        for g in rule["apiGroups"]
        for r in rule["resources"]
        if {"get", "list"} <= set(rule["verbs"])
    }
    assert ("apps", "deployments") in granted and ("apps", "statefulsets") in granted


def test_grader_fails_on_a_zero_pod_deployment_and_prints_the_denial_event():
    short = [{"ns": "healing", "name": "estate", "desired": 1, "available": 0}]
    rc, out = _grade(_receipt(short))
    assert rc == 1
    assert "healing/estate available=0/1" in out
    assert "require-pod-probes" in out  # the denial event travels with the verdict


def test_grader_passes_when_no_workload_is_short():
    rc, out = _grade(_receipt([]))
    assert rc == 0, out


def test_a_receipt_without_the_count_grades_fail_never_silently_ok():
    rc, out = _grade(_receipt([], with_count=False))
    assert rc == 1
    assert "deploy_short" in out

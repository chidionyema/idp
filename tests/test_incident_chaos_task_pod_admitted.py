"""crew#292 CP4, 2026-08-26: the receipt step of platform/chaos/backstage-pod-kill.yaml is a
Chaos Mesh Task pod (owner kind WorkflowNode) that runs one command and exits. The cluster's
require-pod-probes admitted Job-owned pods only (admit-job-pods.yaml), so this pod would have
been refused at admission, after every CI gate had passed. Rule (rung 4): the Task pod, shaped
exactly as the manifest declares it, passes the pinned policy set when owned by a WorkflowNode
and is still refused by require-pod-probes when owned by a ReplicaSet."""
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICIES = ROOT / "tests" / "fixtures" / "kyverno" / "upstream"


def _task_container():
    docs = list(yaml.safe_load_all(open(ROOT / "platform" / "chaos" / "backstage-pod-kill.yaml")))
    sched = next(d for d in docs if d and d.get("kind") == "Schedule")
    tpl = next(t for t in sched["spec"]["workflow"]["templates"] if t.get("templateType") == "Task")
    return tpl["task"]["container"], tpl["task"].get("volumes", [])


def _pod(owner_kind):
    c, vols = _task_container()
    return {
        "apiVersion": "v1", "kind": "Pod",
        "metadata": {"name": "receipt", "namespace": "backstage",
                     "ownerReferences": [{"apiVersion": "chaos-mesh.org/v1alpha1", "kind": owner_kind,
                                          "name": "backstage-pod-kill", "uid": "0"}]},
        "spec": {"restartPolicy": "Never", "containers": [c], "volumes": vols},
    }


def _judge(pod, tmp_path):
    if not (shutil.which("kyverno") and shutil.which("kubectl")):
        pytest.skip("kyverno and kubectl CLIs are required; CI installs both")
    pol = tmp_path / "policies.yaml"
    r = subprocess.run(["kubectl", "kustomize", str(POLICIES)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    pol.write_text(r.stdout)
    res = tmp_path / "pod.yaml"
    res.write_text(yaml.safe_dump(pod))
    out = subprocess.run(["kyverno", "apply", str(pol), "--resource", str(res)], capture_output=True, text=True)
    return out.stdout + out.stderr


def test_workflow_task_pod_is_admitted(tmp_path):
    out = _judge(_pod("WorkflowNode"), tmp_path)
    assert "fail: 0" in out.replace(",", "").lower() or "0 failed" in out.lower() or "fail: 0" in out, out


def test_the_same_pod_under_a_replicaset_is_refused_for_probes(tmp_path):
    out = _judge(_pod("ReplicaSet"), tmp_path)
    assert "require-pod-probes" in out and ("fail" in out.lower()), out

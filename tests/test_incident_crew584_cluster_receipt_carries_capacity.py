"""crew#584 (founder, 2026-08-29): "why 4 cores, do we need all that capacity? who made the call,
do we have utilisation metrics?" The node went 4 -> 6 OCPU (#456) and nobody had a number: no job
recorded what the cluster actually uses against what it pays for. The 15-minute cluster receipt now
carries a capacity block per node (allocatable, requested, used from metrics.k8s.io) and the reader
prints it on every read, so the question always has a measured answer. A receipt without the row
grades FAIL, an unreadable metrics API grades FAIL with its error; neither is ever silently clean."""
import json
import os
import pathlib
import shutil
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEAD = json.dumps({"last-modified": "Thu, 27 Aug 2026 19:00:03 GMT", "date": "Thu, 27 Aug 2026 19:00:05 GMT", "content-length": "10"})
MANIFEST = ROOT / "platform" / "state" / "cluster-state.yaml"
GREEN = ("nodes=1 ready=1 pods=3 pods_not_ready=0 flux=1 flux_not_ready=0 ds=1 ds_short=0 events_warning=0"
         " monitoring_rules=3 alert_watchdog=1")


def _tree(tmp_path, body, name="idp"):
    idp = tmp_path / name; (idp / "bin").mkdir(parents=True)
    shutil.copy(ROOT / "bin" / "idp-cluster-state", idp / "bin" / "idp-cluster-state")
    shutil.copytree(ROOT / "bin" / "lib", idp / "bin" / "lib")
    (idp / "receipt").write_text(body)
    shim = idp / "bin" / "idp-cloud"
    shim.write_text("#!/bin/sh\ncase \"$*\" in\n  *\"object head\"*) printf '%s' '" + HEAD + "';;\n  *\"object get\"*) cat \"$(dirname \"$0\")/../receipt\";;\nesac\n")
    shim.chmod(0o755)
    return idp


def _grade(idp):
    env = {**os.environ, "CLUSTER_STATE_MAX_AGE_MIN": "999999999"}
    return subprocess.run([str(idp / "bin" / "idp-cluster-state")], capture_output=True, text=True, env=env)


def _collector():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    return docs, [d for d in docs if d["kind"] == "ConfigMap"][0]["data"]["collect.py"]


def test_rbac_grants_the_metrics_api_the_collector_reads():
    docs, src = _collector()
    assert '"/apis/metrics.k8s.io/v1beta1/nodes"' in src
    role = [d for d in docs if d["kind"] == "ClusterRole"][0]
    rule = [r for r in role["rules"] if "metrics.k8s.io" in r["apiGroups"]]
    assert rule and "nodes" in rule[0]["resources"] and {"get", "list"} <= set(rule[0]["verbs"]), role["rules"]


def test_collector_computes_used_requested_and_allocatable_per_node():
    _, src = _collector()
    # run the collector's capacity arithmetic against a fake API: 1 node, 4 cores / 24 GiB allocatable,
    # 1 running pod requesting 500m / 1Gi, metrics reporting 1200m / 6Gi used.
    fake = {
        "/api/v1/nodes": {"items": [{"metadata": {"name": "n1"}, "status": {"conditions": [{"type": "Ready", "status": "True"}],
                                                                        "nodeInfo": {"kubeletVersion": "v1.33"},
                                                                        "allocatable": {"cpu": "4", "memory": "25165824Ki"}}}]},
        "/api/v1/pods": {"items": [
            {"metadata": {"name": "p", "namespace": "a"}, "spec": {"nodeName": "n1", "containers": [{"name": "c", "resources": {"requests": {"cpu": "500m", "memory": "1Gi"}}}]},
             "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}]}},
            {"metadata": {"name": "done", "namespace": "a"}, "spec": {"nodeName": "n1", "containers": [{"name": "c", "resources": {"requests": {"cpu": "3", "memory": "10Gi"}}}]},
             "status": {"phase": "Succeeded"}}]},
        "/apis/metrics.k8s.io/v1beta1/nodes": {"items": [{"metadata": {"name": "n1"}, "usage": {"cpu": "1200m", "memory": "6291456Ki"}}]},
    }
    start = src.index("def qty(v):"); end = src.index("head = (f\"ok cluster-state")
    block = src[start:end]
    ns = {"get": lambda p: fake[p], "nodes": fake["/api/v1/nodes"]["items"], "pods": fake["/api/v1/pods"]["items"]}
    exec(block, ns)
    row = ns["capacity"][0]
    assert row == {"name": "n1", "cpu_allocatable": 4.0, "memory_allocatable_gb": 24.0, "cpu_requested": 0.5, "memory_requested_gb": 1.0,
                   "cpu_used": 1.2, "memory_used_gb": 6.0, "cpu_used_pct": 30, "memory_used_pct": 25, "cpu_requested_pct": 12, "memory_requested_pct": 4}, row
    assert (ns["cpu_used_pct"], ns["mem_used_pct"], ns["cpu_req_pct"], ns["mem_req_pct"]) == (30, 25, 12, 4)
    assert ns["cap_error"] == ""


def test_collector_records_a_metrics_read_failure_instead_of_dropping_it():
    _, src = _collector()
    def get(p):
        if "metrics" in p: raise RuntimeError("403 forbidden")
        return {"items": []}
    start = src.index("def qty(v):"); end = src.index("head = (f\"ok cluster-state")
    ns = {"get": get, "nodes": [{"metadata": {"name": "n1"}, "status": {"allocatable": {"cpu": "2", "memory": "1Gi"}}}], "pods": []}
    exec(src[start:end], ns)
    assert ns["cap_error"].startswith("metrics.k8s.io nodes: 403 forbidden")
    assert ns["cpu_used_pct"] == -1 and ns["capacity"][0]["cpu_used"] is None


def test_reader_prints_the_capacity_row_in_plain_words(tmp_path):
    body = {"capacity": [{"name": "n1", "cpu_allocatable": 4.0, "memory_allocatable_gb": 24.0, "cpu_requested": 0.5, "memory_requested_gb": 1.0,
                          "cpu_used": 1.2, "memory_used_gb": 6.0, "cpu_used_pct": 30, "memory_used_pct": 25, "cpu_requested_pct": 12, "memory_requested_pct": 4}],
            "capacity_error": ""}
    line1 = f"ok cluster-state at 2026-08-29T02:00:03Z {GREEN} cpu_used_pct=30 mem_used_pct=25 cpu_req_pct=12 mem_req_pct=4"
    r = _grade(_tree(tmp_path, line1 + "\n" + json.dumps(body) + "\n"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok      capacity       cpu used 30% requested 12%, memory used 25% requested 4% of what is paid for" in r.stdout, r.stdout
    assert "node n1: cpu 1.2/4.0 cores used (30%)" in r.stdout, r.stdout


def test_reader_fails_a_receipt_without_capacity_or_with_unreadable_metrics(tmp_path):
    old = f"ok cluster-state at 2026-08-29T02:00:03Z {GREEN}\n{{}}\n"
    r = _grade(_tree(tmp_path, old))
    assert r.returncode == 1 and "FAIL    capacity       receipt carries no cpu_used_pct" in r.stdout, r.stdout + r.stderr
    blind = (f"ok cluster-state at 2026-08-29T02:00:03Z {GREEN} cpu_used_pct=-1 mem_used_pct=-1 cpu_req_pct=12 mem_req_pct=4\n"
             + json.dumps({"capacity": [], "capacity_error": "metrics.k8s.io nodes: 403 forbidden"}) + "\n")
    r = _grade(_tree(tmp_path, blind, "idp2"))
    assert r.returncode == 1 and "FAIL    capacity       usage unreadable: metrics.k8s.io nodes: 403 forbidden" in r.stdout, r.stdout + r.stderr

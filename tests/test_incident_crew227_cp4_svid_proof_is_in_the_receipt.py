"""crew#227 CP4, 2026-08-27: oke-check 33040809029 showed spire-agent 1/1 and the HelmRelease
Ready, and the box still could not be ticked, because nothing in the receipt says a workload is
registered for an SVID; the collector has no kubectl exec into spire-server. Rule: the receipt
carries every ClusterSPIFFEID with the controller-manager's stats and every pod that mounts the
csi.spiffe.io driver, and the ClusterRole allows the list. Rung 4, incident test, both ways:
a pod with the csi volume is named, a pod without one is not, a failed list is recorded.
Third row (idp#329 follow-up, first receipt 33042911059 showed csi_workloads [] and no possession proof):
a finished CSI workload's log yields its SPIFFE IDs; a log that could not be read is recorded as an error row;
a pod that has not finished is not asked.
Fourth row (idp#336 residual, 07:00Z receipt 33048165522): every proof pod said "workload attestation failed"
and the receipt could not say why; the spire-agent pods' error/warning/attest log lines are a row, a read
that failed is an error row, a pod that is not the agent is not asked."""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]


def test_receipt_names_spiffe_ids_and_csi_workloads_and_the_role_allows_the_list():
    docs = _docs()
    role = next(d for d in docs if d["kind"] == "ClusterRole")
    assert any("spire.spiffe.io" in r["apiGroups"] and "clusterspiffeids" in r["resources"] for r in role["rules"])
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    compile(collect, "collect.py", "exec")
    assert '"spiffe": spiffe' in collect
    src = collect.split("def pod_log", 1)[1].split("spiffe = spiffe_rows()", 1)[0]
    csi = [{"name": "s", "csi": {"driver": "csi.spiffe.io"}}]
    pods = [
        {"metadata": {"namespace": "a", "name": "with-svid"}, "status": {"phase": "Succeeded"},
         "spec": {"containers": [{"name": "fetch"}], "volumes": csi}},
        {"metadata": {"namespace": "a", "name": "log-broken"}, "status": {"phase": "Succeeded"},
         "spec": {"containers": [{"name": "fetch"}], "volumes": csi}},
        {"metadata": {"namespace": "a", "name": "still-running"}, "status": {"phase": "Running"},
         "spec": {"containers": [{"name": "fetch"}], "volumes": csi}},
        {"metadata": {"namespace": "a", "name": "plain"}, "spec": {"volumes": [{"name": "d", "emptyDir": {}}]}},
        {"metadata": {"namespace": "s", "name": "spire-agent-x", "labels": {"app.kubernetes.io/name": "agent", "app.kubernetes.io/instance": "spire"}},
         "status": {"phase": "Running"}, "spec": {"nodeName": "n1", "containers": [{"name": "spire-agent"}], "volumes": []}},
        {"metadata": {"namespace": "s", "name": "spire-agent-broken", "labels": {"app.kubernetes.io/name": "agent", "app.kubernetes.io/instance": "spire"}},
         "status": {"phase": "Running"}, "spec": {"nodeName": "n2", "containers": [{"name": "spire-agent"}], "volumes": []}},
        {"metadata": {"namespace": "s", "name": "spire-server-0", "labels": {"app.kubernetes.io/name": "server", "app.kubernetes.io/instance": "spire"}},
         "status": {"phase": "Running"}, "spec": {"containers": [{"name": "spire-server"}], "volumes": []}},
    ]
    agent_log = ('time=1 level=info msg="Node attestation was successful"\ntime=2 level=info msg=quiet\n'
                 'time=3 level=error msg="Failed to collect all selectors for PID" error="dial tcp 127.0.0.1:10250"\n')
    server_log = ('time=4 level=info msg="Created entry" spiffe_id=spiffe://estate/ns/a/sa/proof parent_id=spiffe://estate/spire/agent/k8s_psat/estate/n1\n'
                  'time=5 level=info msg=quiet\n')
    stub = ("def pod_log(ns, name, c, tail=20):\n"
            "    if name in ('log-broken', 'spire-agent-broken'): return 'log read failed: 500'\n"
            f"    if name == 'spire-agent-x': return {agent_log!r}\n"
            f"    if name == 'spire-server-0': return {server_log!r}\n"
            "    return 'SPIFFE ID:\\t\\tspiffe://estate/ns/a/sa/proof\\nyours\\n'\n")
    svids = [{"pod": "a/with-svid", "container": "fetch", "spiffe_ids": ["spiffe://estate/ns/a/sa/proof"], "error": ""},
             {"pod": "a/log-broken", "container": "fetch", "spiffe_ids": [], "error": "log read failed: 500"}]
    csi_workloads = ["a/log-broken", "a/still-running", "a/with-svid"]
    ids = {"items": [{"metadata": {"name": "agents"}, "status": {"stats": {"podsSelected": 3, "entriesToRender": 3}}}]}
    prog = (f"pods = {pods!r}\nimport json, re\n"
            f"def get(path): return {ids!r}\n"
            "def pod_log" + src + stub + "\nprint(json.dumps(spiffe_rows()))\n")
    got = json.loads(subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True).stdout)
    agents = [{"pod": "s/spire-agent-x", "node": "n1", "error": "",
               "lines": ['time=1 level=info msg="Node attestation was successful"',
                         'time=3 level=error msg="Failed to collect all selectors for PID" error="dial tcp 127.0.0.1:10250"']},
              {"pod": "s/spire-agent-broken", "node": "n2", "lines": [], "error": "log read failed: 500"}]
    server = [{"pod": "s/spire-server-0", "container": "spire-server", "error": "",
               "lines": ['time=4 level=info msg="Created entry" spiffe_id=spiffe://estate/ns/a/sa/proof parent_id=spiffe://estate/spire/agent/k8s_psat/estate/n1']}]
    assert got == {"clusterspiffeids": [{"name": "agents", "podsSelected": 3, "entriesToRender": 3}],
                   "error": "", "csi_workloads": csi_workloads, "svids": svids, "agents": agents, "server": server}
    failing = (f"pods = {pods!r}\nimport json, re\n"
               "def get(path): raise RuntimeError('403 forbidden')\n"
               "def pod_log" + src + stub + "\nprint(json.dumps(spiffe_rows()))\n")
    got = json.loads(subprocess.run([sys.executable, "-c", failing], capture_output=True, text=True, check=True).stdout)
    assert got["clusterspiffeids"] is None and "403" in got["error"] and got["csi_workloads"] == csi_workloads and got["svids"] == svids and got["agents"] == agents and got["server"] == server

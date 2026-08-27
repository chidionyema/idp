"""crew#227 CP4, 2026-08-27: oke-check 33040809029 showed spire-agent 1/1 and the HelmRelease
Ready, and the box still could not be ticked, because nothing in the receipt says a workload is
registered for an SVID; the collector has no kubectl exec into spire-server. Rule: the receipt
carries every ClusterSPIFFEID with the controller-manager's stats and every pod that mounts the
csi.spiffe.io driver, and the ClusterRole allows the list. Rung 4, incident test, both ways:
a pod with the csi volume is named, a pod without one is not, a failed list is recorded."""
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
    src = collect.split("def spiffe_rows", 1)[1].split("spiffe = spiffe_rows()", 1)[0]
    pods = [
        {"metadata": {"namespace": "a", "name": "with-svid"}, "spec": {"volumes": [{"name": "s", "csi": {"driver": "csi.spiffe.io"}}]}},
        {"metadata": {"namespace": "a", "name": "plain"}, "spec": {"volumes": [{"name": "d", "emptyDir": {}}]}},
    ]
    ids = {"items": [{"metadata": {"name": "agents"}, "status": {"stats": {"podsSelected": 3, "entriesToRender": 3}}}]}
    prog = (f"pods = {pods!r}\nimport json\n"
            f"def get(path): return {ids!r}\n"
            "def spiffe_rows" + src + "\nprint(json.dumps(spiffe_rows()))\n")
    got = json.loads(subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True).stdout)
    assert got == {"clusterspiffeids": [{"name": "agents", "podsSelected": 3, "entriesToRender": 3}],
                   "error": "", "csi_workloads": ["a/with-svid"]}
    failing = (f"pods = {pods!r}\nimport json\n"
               "def get(path): raise RuntimeError('403 forbidden')\n"
               "def spiffe_rows" + src + "\nprint(json.dumps(spiffe_rows()))\n")
    got = json.loads(subprocess.run([sys.executable, "-c", failing], capture_output=True, text=True, check=True).stdout)
    assert got["clusterspiffeids"] is None and "403" in got["error"] and got["csi_workloads"] == ["a/with-svid"]

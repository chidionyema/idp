"""flannel-off: the playbook that ends the two-dataplane incident of 2026-09-09.

Two VXLAN dataplanes shared port 4789 and the cross-node path died. These grade the shape the
playbook must keep: it is reachable, it refuses to act unless Calico owns every pod address, it
parks flannel reversibly rather than deleting it, and it proves the cross-node hop afterwards.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "bin" / "idp-oke-break-glass"
WORKFLOW = ROOT / ".github" / "workflows" / "oke-check.yml"


def body() -> str:
    text = SCRIPT.read_text()
    start = text.index("pb_flannel_off() {")
    depth, i = 0, start
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
        i += 1
    raise AssertionError("pb_flannel_off never closes")


def test_listed_and_dispatchable():
    names = subprocess.run(
        [str(SCRIPT), "--list"], capture_output=True, text=True, check=True
    ).stdout.split()
    assert "flannel-off" in names
    assert "flannel-off) pb_flannel_off ;;" in SCRIPT.read_text()


def test_offered_by_the_workflow():
    line = [
        ln
        for ln in WORKFLOW.read_text().splitlines()
        if "options:" in ln and "cni-resync" in ln
    ]
    assert line and "flannel-off" in line[0]


def test_guards_run_before_any_change():
    b = body()
    park = b.index("kube-flannel-ds --type=merge")
    for guard in ("guard-calico", "guard-ipam"):
        assert b.index(guard) < park, (
            f"{guard} must be graded before flannel is touched"
        )
    assert "FAILED=" in b.split("kube-flannel-ds --type=merge")[0]


def test_parks_rather_than_deletes():
    b = body()
    assert "patch ds kube-flannel-ds" in b
    assert "nodeSelector" in b
    assert "delete ds kube-flannel-ds" not in b, (
        "flannel is parked reversibly, never deleted"
    )


def test_proves_the_cross_node_hop_from_each_node():
    b = body()
    assert "spec.nodeName!=" in b, "targets must be pods on the OTHER node"
    assert "tcp_probe " in b
    assert "dns_probe " in b
    assert "rollout restart ds calico-node" in b

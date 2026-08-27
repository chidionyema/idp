"""crew#516 CP4 (2026-08-27): the one worker node evicted hermes-agent-gateway at 5.9 GB free of
its 50 GB boot volume, and a BASIC cluster has no node cycling, so a bigger boot volume reaches a
NEW node only. `bin/idp-oke-surge-node` grows the pool to 2, waits for the second ACTIVE node,
then deletes the old one with the size decremented only once the new one is Ready in the cluster's
own receipt state/cluster, written after the surge began (ACTIVE is the instance, not the kubelet;
a runner has no kube path; on BASIC the only node has no path back). Proved with `oci`/`tofu` shims that record
every call: the order is grow -> wait -> delete-old-with-decrement, the deleted node is the OLD
one, and two ACTIVE nodes (a surge already in flight) are refused before any write.
`platform/oci/main.tf` carries the 100 GB boot volume and `oke-check.yml` offers `surge-node`.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

OCI_SHIM = r'''#!/bin/sh
echo "$*" >> "$SHIM_LOG"
case "$*" in
  *"node-pool list"*) echo "ocid1.nodepool.pool";;
  *"private-ip"*) echo 10.0.0.9;;
  *"node-pool get"*) cat "$SHIM_NODES";;
  *"os object get"*) printf '{"at":"%s","nodes":[{"name":"10.0.0.9","ready":%s}]}' "$KUBE_AT" "$KUBE_READY";;
  *"node-pool update"*) echo '["ocid1.node.old","ocid1.node.new"]' > "$SHIM_NODES";;
  *"delete-node"*) echo '["ocid1.node.new"]' > "$SHIM_NODES";;
esac
'''
TOFU_SHIM = '#!/bin/sh\necho ocid1.cluster.estate\n'


def _tree(tmp_path, nodes, kube_ready="true", kube_at="2999-01-01T00:00:00Z"):
    idp = tmp_path / "idp"; (idp / "bin").mkdir(parents=True); (idp / "platform/oci").mkdir(parents=True)
    shutil.copy(ROOT / "bin/idp-oke-surge-node", idp / "bin/idp-oke-surge-node")
    (idp / "platform/oci/terraform.tfvars").write_text('tenancy_ocid = "t"\ncompartment_ocid            = "ocid1.compartment.c"\n')
    shim = tmp_path / "shim"; shim.mkdir()
    for name, body in (("oci", OCI_SHIM), ("tofu", TOFU_SHIM)):
        f = shim / name; f.write_text(body); f.chmod(f.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "nodes.json").write_text(json.dumps(nodes))
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "SHIM_LOG": str(tmp_path / "log"),
           "SHIM_NODES": str(tmp_path / "nodes.json"), "SURGE_READY_ROUNDS": "2", "SURGE_POLL_SECONDS": "0", "SURGE_READY_POLL_SECONDS": "0", "KUBE_READY": kube_ready, "KUBE_AT": kube_at}
    r = subprocess.run([str(idp / "bin/idp-oke-surge-node")], env=env, text=True, capture_output=True)
    log = (tmp_path / "log").read_text().splitlines() if (tmp_path / "log").exists() else []
    return r, log


def test_the_surge_grows_waits_then_deletes_the_old_node_with_the_size_decremented(tmp_path):
    r, log = _tree(tmp_path, ["ocid1.node.old"])
    assert r.returncode == 0, r.stdout + r.stderr
    writes = [l for l in log if "update" in l or "delete-node" in l]
    assert len(writes) == 2 and "node-pool update" in writes[0] and "--size 2" in writes[0], writes
    assert "delete-node" in writes[1] and "--node-id ocid1.node.old" in writes[1] and "--is-decrement-size true" in writes[1], writes
    assert "--compartment-id ocid1.compartment.c" in log[0] and "--cluster-id ocid1.cluster.estate" in log[0]
    assert "new node ocid1.node.new Ready as 10.0.0.9 (receipt state/cluster written after" in r.stdout
    assert "new node ocid1.node.new ACTIVE, old node ocid1.node.old deleted" in r.stdout
    assert log.index(next(l for l in log if "os object get" in l)) < log.index(writes[1])


def test_a_node_that_is_active_but_never_ready_keeps_the_old_node(tmp_path):
    r, log = _tree(tmp_path, ["ocid1.node.old"], kube_ready="false")
    assert r.returncode == 4 and "never Ready in the cluster receipt; old node ocid1.node.old kept, pool left at size 2" in r.stdout, r.stdout + r.stderr
    assert not [l for l in log if "delete-node" in l]


def test_a_receipt_written_before_the_surge_is_not_evidence(tmp_path):
    # ready=true but stale: the row could describe a node that no longer exists
    r, log = _tree(tmp_path, ["ocid1.node.old"], kube_ready="true", kube_at="2000-01-01T00:00:00Z")
    assert r.returncode == 4 and not [l for l in log if "delete-node" in l], r.stdout + r.stderr


def test_two_active_nodes_are_refused_before_any_write(tmp_path):
    r, log = _tree(tmp_path, ["ocid1.node.a", "ocid1.node.b"])
    assert r.returncode == 3 and "found 2; refusing" in r.stdout, r.stdout + r.stderr
    assert not [l for l in log if "update" in l or "delete-node" in l]


def test_the_pool_carries_the_bigger_boot_volume_and_the_workflow_offers_the_surge():
    tf = (ROOT / "platform/oci/main.tf").read_text()
    m = re.search(r"boot_volume_size\s*=\s*(\d+)", tf)
    assert m and int(m.group(1)) >= 100, m and m.group(0)
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    assert "surge-node" in wf[True]["workflow_dispatch"]["inputs"]["mode"]["options"]
    rebuild = (ROOT / "bin/idp-oke-rebuild").read_text()
    assert "--surge-node)" in rebuild and 'step surge-node "$IDP/bin/idp-oke-surge-node"' in rebuild


# crew#516 run 33101801971 (2026-08-27 19:01Z): the new node was Ready in the receipt written at
# 19:00:03Z, but the gate's last reads returned nothing (the run's OIDC session token, minted at
# 18:11Z, had gone stale) and `2>/dev/null` turned that into "never Ready": exit 4, old node kept,
# pool paying for two. A blind read is now BLIND on stderr, three in a row exit 5 and name the
# second half, and `--finish` completes the surge from a fresh run: oldest node deleted with the
# size decremented once a fresh receipt shows the newest node Ready.
FINISH_SHIM = r'''#!/bin/sh
echo "$*" >> "$SHIM_LOG"
case "$*" in
  *"node-pool list"*) echo "ocid1.nodepool.pool";;
  *"time-created"*) cat "$SHIM_NODES";;
  *"os object get"*) [ -n "$KUBE_BODY" ] && printf '%s' "$KUBE_BODY" || { echo "ServiceError: NotAuthenticated" >&2; exit 1; };;
  *"delete-node"*) :;;
esac
'''
FRESH = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
TWO = [{"id": "ocid1.node.old", "ip": "10.0.0.1", "t": "2026-08-01T00:00:00Z"}, {"id": "ocid1.node.new", "ip": "10.0.0.9", "t": "2026-08-27T18:20:00Z"}]


def _finish(tmp_path, body, nodes=TWO):
    idp = tmp_path / "idp"; (idp / "bin").mkdir(parents=True); (idp / "platform/oci").mkdir(parents=True)
    shutil.copy(ROOT / "bin/idp-oke-surge-node", idp / "bin/idp-oke-surge-node")
    (idp / "platform/oci/terraform.tfvars").write_text('compartment_ocid = "ocid1.compartment.c"\n')
    shim = tmp_path / "shim"; shim.mkdir()
    for name, text in (("oci", FINISH_SHIM), ("tofu", TOFU_SHIM)):
        f = shim / name; f.write_text(text); f.chmod(f.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "nodes.json").write_text(json.dumps(nodes))
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "SHIM_LOG": str(tmp_path / "log"), "SHIM_NODES": str(tmp_path / "nodes.json"), "KUBE_BODY": body}
    r = subprocess.run([str(idp / "bin/idp-oke-surge-node"), "--finish"], env=env, text=True, capture_output=True)
    log = (tmp_path / "log").read_text().splitlines() if (tmp_path / "log").exists() else []
    return r, log


def test_a_blind_receipt_read_is_named_and_exits_5_after_three_in_a_row_without_deleting(tmp_path):
    blind = OCI_SHIM.replace('''*"os object get"*) printf '{"at":"%s","nodes":[{"name":"10.0.0.9","ready":%s}]}' "$KUBE_AT" "$KUBE_READY";;''',
                             '''*"os object get"*) echo "ServiceError: NotAuthenticated" >&2; exit 1;;''')
    assert blind != OCI_SHIM
    idp = tmp_path / "idp"; (idp / "bin").mkdir(parents=True); (idp / "platform/oci").mkdir(parents=True)
    shutil.copy(ROOT / "bin/idp-oke-surge-node", idp / "bin/idp-oke-surge-node")
    (idp / "platform/oci/terraform.tfvars").write_text('compartment_ocid = "ocid1.compartment.c"\n')
    shim = tmp_path / "shim"; shim.mkdir()
    for name, text in (("oci", blind), ("tofu", TOFU_SHIM)):
        f = shim / name; f.write_text(text); f.chmod(f.stat().st_mode | stat.S_IEXEC)
    (tmp_path / "nodes.json").write_text(json.dumps(["ocid1.node.old"]))
    env = {**os.environ, "PATH": f"{shim}:{os.environ['PATH']}", "SHIM_LOG": str(tmp_path / "log"), "SHIM_NODES": str(tmp_path / "nodes.json"),
           "SURGE_READY_ROUNDS": "10", "SURGE_POLL_SECONDS": "0", "SURGE_READY_POLL_SECONDS": "0"}
    r = subprocess.run([str(idp / "bin/idp-oke-surge-node")], env=env, text=True, capture_output=True)
    log = (tmp_path / "log").read_text().splitlines()
    assert r.returncode == 5, r.stdout + r.stderr
    assert r.stderr.count("BLIND   receipt state/cluster unreadable: ServiceError: NotAuthenticated") == 3, r.stderr
    assert "went BLIND 3 times running" in r.stdout and "mode=surge-finish" in r.stdout, r.stdout
    assert not [l for l in log if "delete-node" in l]


def test_finish_deletes_the_oldest_node_once_a_fresh_receipt_shows_the_newest_ready(tmp_path):
    r, log = _finish(tmp_path, json.dumps({"at": FRESH, "nodes": [{"name": "10.0.0.1", "ready": True}, {"name": "10.0.0.9", "ready": True}]}))
    assert r.returncode == 0, r.stdout + r.stderr
    d = [l for l in log if "delete-node" in l]
    assert len(d) == 1 and "--node-id ocid1.node.old" in d[0] and "--is-decrement-size true" in d[0], d
    assert "new node ocid1.node.new Ready as 10.0.0.9" in r.stdout and "old node ocid1.node.old deleted, pool back to size 1" in r.stdout


def test_finish_keeps_the_old_node_while_the_newest_is_not_ready(tmp_path):
    r, log = _finish(tmp_path, json.dumps({"at": FRESH, "nodes": [{"name": "10.0.0.1", "ready": True}, {"name": "10.0.0.9", "ready": False}]}))
    assert r.returncode == 4 and "not Ready in the receipt yet; old node ocid1.node.old kept" in r.stdout, r.stdout + r.stderr
    assert not [l for l in log if "delete-node" in l]


def test_finish_is_blind_not_not_ready_when_the_receipt_cannot_be_read(tmp_path):
    r, log = _finish(tmp_path, "")
    assert r.returncode == 5 and "BLIND, receipt state/cluster unreadable: ServiceError: NotAuthenticated" in r.stdout, r.stdout + r.stderr
    assert not [l for l in log if "delete-node" in l]


def test_finish_refuses_a_stale_receipt_and_a_pool_without_two_nodes(tmp_path):
    r, log = _finish(tmp_path, json.dumps({"at": "2026-08-01T00:00:00Z", "nodes": [{"name": "10.0.0.9", "ready": True}]}))
    assert r.returncode == 3 and "STALE receipt" in r.stdout and not [l for l in log if "delete-node" in l], r.stdout + r.stderr
    r, log = _finish(tmp_path / "one", json.dumps({"at": FRESH, "nodes": [{"name": "10.0.0.9", "ready": True}]}), nodes=TWO[1:])
    assert r.returncode == 3 and "expected 2 ACTIVE nodes in the pool, found 1" in r.stdout and not [l for l in log if "delete-node" in l], r.stdout + r.stderr


def test_the_workflow_and_the_rebuild_offer_surge_finish():
    wf = yaml.safe_load((ROOT / ".github/workflows/oke-check.yml").read_text())
    assert "surge-finish" in wf[True]["workflow_dispatch"]["inputs"]["mode"]["options"]
    assert '--surge-finish)' in (ROOT / "bin/idp-oke-rebuild").read_text()

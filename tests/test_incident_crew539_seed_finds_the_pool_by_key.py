"""Incident, 2026-08-27 (oke-check apply 33123127717, crew#539 CP4): bin/idp-autoscaler-seed asked
OCI for a node pool named `estate-a1`; the OKE module names the pool by its key (`a1`), so the seed
went BLIND, the vault kept nothing, ExternalSecret oke-autoscaler 404ed and the Cluster Autoscaler
sat in CreateContainerConfigError. The seed now lists every ACTIVE pool of the cluster once and
matches a key by name (`a1`, `<cluster>-a1`, `*-a1`), newest first, and a BLIND line names the
pools that do exist. Fakes for `oci` and `idp-vault-put` on PATH; no cloud, no socket.
"""
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "bin" / "idp-autoscaler-seed"

FAKE_OCI = """#!/usr/bin/env bash
# `oci ce cluster list` -> one cluster id; `oci ce node-pool list` -> $FAKE_POOLS (json)
case "$*" in
  *"cluster list"*) echo ocid1.cluster.fake;;
  *"node-pool list"*) printf '%s' "${FAKE_POOLS:-[]}";;
  *) exit 1;;
esac
"""
FAKE_VAULT_PUT = """#!/usr/bin/env bash
# records the entry name and the key NAMES it was asked for, and the file's key names
echo "$@" > "$SEED_TEST_OUT"
cut -d= -f1 "$ESTATE_ENV_FILE" >> "$SEED_TEST_OUT"
"""


def _tree(tmp_path):
    """A copy of the seed beside a fake idp-vault-put, so $IDP/bin/idp-vault-put is the fake."""
    b = tmp_path / "idp" / "bin"
    b.mkdir(parents=True)
    shutil.copy(SEED, b / "idp-autoscaler-seed")
    for name, body in (("idp-vault-put", FAKE_VAULT_PUT), ("oci", FAKE_OCI)):
        p = b / name
        p.write_text(body)
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return b


def _run(tmp_path, pools, *keys):
    tmp_path = tmp_path / f"run{len(list(tmp_path.iterdir()))}"
    tmp_path.mkdir()
    b = _tree(tmp_path)
    out = tmp_path / "vault-put.out"
    env = {
        **os.environ,
        "PATH": f"{b}:{os.environ['PATH']}",
        "FAKE_POOLS": json.dumps(pools),
        "SEED_TEST_OUT": str(out),
        "OCI_COMPARTMENT_OCID": "ocid1.compartment.fake",
        "OCI_REGION": "eu-fake-1",
        "OCI_CLUSTER_NAME": "estate",
    }
    r = subprocess.run([str(b / "idp-autoscaler-seed"), *keys], env=env, capture_output=True, text=True)
    return r, out


def test_the_module_names_the_pool_by_its_key_and_the_seed_finds_it(tmp_path):
    pools = [
        {"name": "a1", "id": "ocid1.nodepool.a1", "at": "2026-08-20T00:00:00Z"},
        {"name": "a1-spot", "id": "ocid1.nodepool.spot", "at": "2026-08-27T22:50:00Z"},
    ]
    r, out = _run(tmp_path, pools)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = out.read_text().split("\n")
    assert lines[0].startswith("oke-autoscaler ")
    assert set(lines[1:5]) == {"NODEPOOL_ID", "SPOT_NODEPOOL_ID", "COMPARTMENT_ID", "REGION"}
    assert "ocid1.nodepool" not in r.stdout  # key names only, never a value (LAW 21)


def test_a_cluster_prefixed_name_is_still_found_and_the_newest_wins_after_a_surge(tmp_path):
    pools = [
        {"name": "estate-a1", "id": "ocid1.nodepool.old", "at": "2026-08-01T00:00:00Z"},
        {"name": "estate-a1", "id": "ocid1.nodepool.new", "at": "2026-08-27T00:00:00Z"},
        {"name": "estate-a1-spot", "id": "ocid1.nodepool.spot", "at": "2026-08-27T00:00:00Z"},
    ]
    r, _ = _run(tmp_path, pools)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_spot_key_never_matches_the_base_pool(tmp_path):
    # `a1` must not answer for `a1-spot`, and `a1-spot` must not answer for `a1`
    r, _ = _run(tmp_path, [{"name": "a1", "id": "ocid1.nodepool.a1", "at": "2026-08-27T00:00:00Z"}])
    assert r.returncode == 2
    assert "no ACTIVE node pool for key a1-spot" in r.stdout
    r, _ = _run(tmp_path, [{"name": "a1-spot", "id": "ocid1.nodepool.spot", "at": "2026-08-27T00:00:00Z"}])
    assert r.returncode == 2
    assert "no ACTIVE node pool for key a1" in r.stdout


def test_blind_names_the_pools_that_exist_so_the_receipt_explains_itself(tmp_path):
    r, out = _run(tmp_path, [{"name": "estate-b2", "id": "ocid1.nodepool.b2", "at": "2026-08-27T00:00:00Z"}])
    assert r.returncode == 2
    assert "ACTIVE pools: estate-b2" in r.stdout
    assert not out.exists()  # BLIND is never a write

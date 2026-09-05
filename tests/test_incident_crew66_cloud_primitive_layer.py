"""crew#66 CP1 / crew#309: 27 operator files called the oci CLI directly. bin/idp-cloud is the one layer; these tests run it on the file backend so no network is touched, and pin that the first three callers no longer name the CLI.
"""
import json
import os
import pathlib
import re
import subprocess

import pytest
from email.utils import parsedate_to_datetime

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLOUD = ROOT / "bin" / "idp-cloud"

ENV = {**os.environ, "IDP_CLOUD_BACKEND": "file"}


def _run(tmp_path, *args):
    env = {**ENV, "IDP_CLOUD_FILE_ROOT": str(tmp_path)}
    return subprocess.run([str(CLOUD), *args], capture_output=True, text=True, env=env)


def test_object_put_head_get_list_round_trip(tmp_path):
    f = tmp_path / "payload.txt"
    f.write_text("hello\n")
    put = _run(tmp_path, "object", "put", "--bucket", "b", "--name", "state/x", "--file", str(f))
    assert put.returncode == 0, put.stderr
    head = _run(tmp_path, "object", "head", "--bucket", "b", "--name", "state/x")
    assert head.returncode == 0, head.stderr
    info = json.loads(head.stdout)
    assert info["content-length"] == 6
    parsedate_to_datetime(info["last-modified"])  # RFC 1123 parses cleanly
    get = _run(tmp_path, "object", "get", "--bucket", "b", "--name", "state/x")
    assert get.returncode == 0 and get.stdout == "hello\n"
    listing = _run(tmp_path, "object", "list", "--bucket", "b")
    assert listing.stdout.strip() == "state/x"
    none = _run(tmp_path, "object", "list", "--bucket", "b", "--prefix", "nope")
    assert none.stdout == ""


def test_object_head_of_a_missing_object_says_notfound_with_exit_1(tmp_path):
    head = _run(tmp_path, "object", "head", "--bucket", "b", "--name", "absent")
    assert head.returncode == 1
    assert "NotFound" in head.stderr


def test_secret_get_and_list_on_the_file_backend(tmp_path):
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "github-app").write_text('{"app_id":1}')
    got = _run(tmp_path, "secret", "get", "github-app")
    assert got.returncode == 0 and got.stdout == '{"app_id":1}'
    listed = _run(tmp_path, "secret", "list")
    assert listed.stdout.strip() == "github-app"
    miss = _run(tmp_path, "secret", "get", "nothing")
    assert miss.returncode == 1 and "NotFound" in miss.stderr


def test_unknown_backend_and_unset_root_are_blind(tmp_path):
    env = {**os.environ, "IDP_CLOUD_BACKEND": "nope"}
    r = subprocess.run([str(CLOUD), "object", "head", "--bucket", "b", "--name", "x"], capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "BLIND" in r.stderr
    env = {**os.environ, "IDP_CLOUD_BACKEND": "file"}  # IDP_CLOUD_FILE_ROOT removed
    r = subprocess.run([str(CLOUD), "object", "head", "--bucket", "b", "--name", "x"], capture_output=True, text=True, env=env)
    assert r.returncode == 2 and "BLIND" in r.stderr


@pytest.mark.parametrize("name", ["idp-cluster-state", "idp-kini-state", "idp-door-heartbeat", "idp-chaos-drill", "idp-science-facts", "idp-telemetry-coverage"])
def test_the_first_three_callers_go_through_the_layer_never_the_cli(name):
    text = (ROOT / "bin" / name).read_text()
    assert '"$IDP/bin/idp-cloud" object head' in text
    assert '"$IDP/bin/idp-cloud" object get' in text
    assert not re.search(r"^\s*[^#]*\boci os object", text, re.M), f"{name} still names the oci CLI"


def test_secret_get_refuses_a_split_store(tmp_path):
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "dup").write_text("value")
    (secrets / "dup.split").write_text("")
    got = _run(tmp_path, "secret", "get", "dup")
    assert got.returncode == 3
    assert "Split" in got.stderr


@pytest.mark.parametrize("name", ["idp-hc-enroll", "idp-login-drill", "idp-trace-drill", "idp-github-app", "idp-vault-put"])
def test_secret_callers_go_through_the_layer(name):
    text = (ROOT / "bin" / name).read_text()
    assert '"$IDP/bin/idp-cloud" secret ' in text
    assert not re.search(r"^\s*[^#]*\boci (vault|secrets)", text, re.M), \
        f"{name} still names the oci CLI for secret reads"


def test_cluster_state_reads_a_file_backend_receipt_end_to_end(tmp_path):
    r"""Build a fresh, all-green receipt on the file backend and let idp-cluster-state grade it.

    The receipt line the python block grades is parsed by `re.finditer(r"(\w+)=(\d+)", line1)`,
    so every value must be a digit and `flux_not_ready`/`ds_short` must both be 0. The body is
    parsed only when the corresponding count is > 0, so empty arrays are fine here.
    """
    receipt_dir = tmp_path / "objects" / "estate-drill-receipts" / "state"
    receipt_dir.mkdir(parents=True)
    head_line = (
        "ok cluster-state at 2026-08-27T00:00:00Z nodes=1 ready=1 pods=0 pods_not_ready=0"
        " flux=0 flux_not_ready=0 ds=0 ds_short=0 events_warning=0"
        " hostnames=0 spiffe_ids=0 spiffe_workloads=0 svids=0 spire_agents=0"
        " oci_pods=0 oci_static_key_pods=0 policy_exceptions=0 monitoring_rules=1 alert_watchdog=1"
        " cpu_used_pct=30 mem_used_pct=25 cpu_req_pct=12 mem_req_pct=4"
    )
    body = {
        "at": "2026-08-27T00:00:00Z",
        "nodes": [],
        "pods_total": 0,
        "pods_not_ready": [],
        "flux": [],
        "flux_not_ready": [],
        "policy_exceptions": [],
        "daemonsets": [],
        "ds_short": [],
        "events_warning": [],
        "hostnames": [],
        "hostnames_error": None,
        "spiffe": {},
        "oci_identity": {"pods": [], "static_key_pods": [], "unknown_identity_pods": []},
    }
    (receipt_dir / "cluster").write_text(head_line + "\n" + json.dumps(body, sort_keys=True) + "\n")

    env = {**os.environ, "IDP_CLOUD_BACKEND": "file", "IDP_CLOUD_FILE_ROOT": str(tmp_path)}
    r = subprocess.run([str(ROOT / "bin" / "idp-cluster-state")], capture_output=True, text=True, env=env)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert r.stdout.startswith("ok ")


def test_secret_put_delete_round_trip(tmp_path):
    f = tmp_path / "payload.json"
    f.write_text('{"a":1}')
    put1 = _run(tmp_path, "secret", "put", "rt", "--file", str(f))
    assert put1.returncode == 0, put1.stderr
    assert put1.stdout == "created"
    got = _run(tmp_path, "secret", "get", "rt")
    assert got.returncode == 0 and got.stdout == '{"a":1}'
    put2 = _run(tmp_path, "secret", "put", "rt", "--file", str(f))
    assert put2.returncode == 0, put2.stderr
    assert put2.stdout == "updated"
    delete = _run(tmp_path, "secret", "delete", "rt")
    assert delete.returncode == 0, delete.stderr
    miss = _run(tmp_path, "secret", "get", "rt")
    assert miss.returncode == 1 and "NotFound" in miss.stderr
    delete2 = _run(tmp_path, "secret", "delete", "rt")
    assert delete2.returncode == 0, delete2.stderr


def test_vault_put_round_trip_on_file_backend(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("A=x\nB=y\n")
    env = {
        **os.environ,
        "IDP_CLOUD_BACKEND": "file",
        "IDP_CLOUD_FILE_ROOT": str(tmp_path),
        "OCI_COMPARTMENT_OCID": "dummy",
        "OCI_CLI_PROFILE": "dummy",
        "ESTATE_ENV_FILE": str(env_file),
    }
    p1 = subprocess.run(
        [str(ROOT / "bin" / "idp-vault-put"), "t1", "KA=A", "KB=B"],
        capture_output=True, text=True, env=env,
    )
    assert p1.returncode == 0, (p1.stdout, p1.stderr)
    assert "created" in p1.stdout, p1.stdout
    secret_path = tmp_path / "secrets" / "t1"
    body = json.loads(secret_path.read_text())
    assert body == {"KA": "x", "KB": "y"}, body
    p2 = subprocess.run(
        [str(ROOT / "bin" / "idp-vault-put"), "--merge", "t1", "KC=B"],
        capture_output=True, text=True, env=env,
    )
    assert p2.returncode == 0, (p2.stdout, p2.stderr)
    assert "updated" in p2.stdout, p2.stdout
    body2 = json.loads(secret_path.read_text())
    assert body2.get("KA") == "x" and body2.get("KB") == "y" and body2.get("KC") == "y", body2


def test_cp5a_secret_describe(tmp_path):
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "withmeta").write_text("secret-bytes")
    (secrets / "withmeta.meta.json").write_text(json.dumps({"id": "ocid1.secret.oc1..abc", "vault-id": "ocid1.vault.oc1..xyz", "key-id": "ocid1.key.oc1..k"}))
    r = _run(tmp_path, "secret", "describe", "withmeta")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"id": "ocid1.secret.oc1..abc", "vault-id": "ocid1.vault.oc1..xyz", "key-id": "ocid1.key.oc1..k"}

    (secrets / "barefile").write_text("bare")
    r = _run(tmp_path, "secret", "describe", "barefile")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout) == {"id": "file:barefile", "vault-id": "file", "key-id": "file"}

    r = _run(tmp_path, "secret", "describe", "absent")
    assert r.returncode == 1
    assert "NotFound" in r.stderr

    (secrets / "splitme").write_text("v")
    (secrets / "splitme.split").write_text("")
    r = _run(tmp_path, "secret", "describe", "splitme")
    assert r.returncode == 3
    assert "Split" in r.stderr


def test_cp5a_secret_list_with_vault_flag(tmp_path):
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "topA").write_text("a")
    (tmp_path / "secrets" / "topB").write_text("b")
    (tmp_path / "vaults" / "v1" / "secrets").mkdir(parents=True)
    (tmp_path / "vaults" / "v1" / "secrets" / "vaultA").write_text("a")
    (tmp_path / "vaults" / "v1" / "secrets" / "vaultB").write_text("b")

    listed = _run(tmp_path, "secret", "list", "--vault", "v1")
    assert listed.returncode == 0, listed.stderr
    assert listed.stdout.strip().splitlines() == ["vaultA", "vaultB"]

    unknown = _run(tmp_path, "secret", "list", "--vault", "nope")
    assert unknown.returncode == 0
    assert unknown.stdout == ""

    plain = _run(tmp_path, "secret", "list")
    assert plain.returncode == 0, plain.stderr
    assert plain.stdout.strip().splitlines() == ["topA", "topB"]


def test_cp5a_vault_list(tmp_path):
    r = _run(tmp_path, "vault", "list")
    assert r.returncode == 0
    assert r.stdout == ""

    vaults = tmp_path / "vaults"
    vaults.mkdir()
    (vaults / "vB").mkdir()
    (vaults / "vB" / "name").write_text("Bravo")
    (vaults / "vA").mkdir()
    (vaults / "vA" / "name").write_text("Alpha")
    (vaults / "vC").mkdir()
    (vaults / "vC" / "name").write_text("Charlie")

    r = _run(tmp_path, "vault", "list")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines() == ["Alpha vA", "Bravo vB", "Charlie vC"]


def test_cp5a_bucket_head(tmp_path):
    r = _run(tmp_path, "bucket", "head", "nope")
    assert r.returncode == 1
    assert "NotFound" in r.stderr
    assert "bucket" in r.stderr

    (tmp_path / "objects" / "estate-drill-receipts").mkdir(parents=True)
    r = _run(tmp_path, "bucket", "head", "estate-drill-receipts")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"


def test_cp5a_header_documents_new_verbs():
    text = (ROOT / "bin" / "idp-cloud").read_text()
    block_lines = []
    for line in text.splitlines():
        if line.startswith("#"):
            block_lines.append(line)
        else:
            break
    block = "\n".join(block_lines)
    assert "secret describe" in block
    assert "--vault" in block
    assert "vault list" in block
    assert "bucket head" in block
    assert "cluster list" in block
    assert "cluster nodepools" in block
    assert "cluster kubeconfig" in block
    assert "--region" in block


def test_cp5d_cluster_list_on_file_backend(tmp_path):
    r = _run(tmp_path, "cluster", "list")
    assert r.returncode == 0
    assert r.stdout == ""   # no clusters/ dir yet

    for cid, name in [("ocid1.cluster.aaa", "Alpha"), ("ocid1.cluster.ccc", "Charlie"), ("ocid1.cluster.bbb", "Bravo")]:
        d = tmp_path / "clusters" / cid
        d.mkdir(parents=True)
        (d / "name").write_text(name)
    r = _run(tmp_path, "cluster", "list")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines() == ["Alpha ocid1.cluster.aaa", "Bravo ocid1.cluster.bbb", "Charlie ocid1.cluster.ccc"]


def test_cp5d_cluster_nodepools_on_file_backend(tmp_path):
    r = _run(tmp_path, "cluster", "nodepools")
    assert r.returncode == 0
    assert r.stdout == ""

    (tmp_path / "nodepools").mkdir()
    for name, state in [("pool-b", "ACTIVE"), ("pool-a", "ACTIVE"), ("pool-c", "UPDATING")]:
        (tmp_path / "nodepools" / name).write_text(state)
    r = _run(tmp_path, "cluster", "nodepools")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines() == ["pool-a ACTIVE", "pool-b ACTIVE", "pool-c UPDATING"]


def test_cp5d_cluster_kubeconfig_copies_the_file_and_chmods_600(tmp_path):
    d = tmp_path / "clusters" / "ocid1.cluster.x"
    d.mkdir(parents=True)
    (d / "kubeconfig").write_text("apiVersion: v1\nclusters: []\n")
    out = tmp_path / "kube"
    r = _run(tmp_path, "cluster", "kubeconfig", "ocid1.cluster.x", "--file", str(out))
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""
    assert out.read_text() == "apiVersion: v1\nclusters: []\n"
    assert (out.stat().st_mode & 0o777) == 0o600


def test_cp5d_cluster_kubeconfig_missing_cluster_is_exit_1_notfound(tmp_path):
    out = tmp_path / "kube"
    r = _run(tmp_path, "cluster", "kubeconfig", "ocid1.cluster.absent", "--file", str(out))
    assert r.returncode == 1
    assert "NotFound" in r.stderr
    assert "ocid1.cluster.absent" in r.stderr
    assert not out.exists()

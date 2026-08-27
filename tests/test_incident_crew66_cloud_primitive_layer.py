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


@pytest.mark.parametrize("name", ["idp-cluster-state", "idp-kini-state", "idp-door-heartbeat"])
def test_the_first_three_callers_go_through_the_layer_never_the_cli(name):
    text = (ROOT / "bin" / name).read_text()
    assert '"$IDP/bin/idp-cloud" object head' in text
    assert '"$IDP/bin/idp-cloud" object get' in text
    assert not re.search(r"^\s*[^#]*\boci os object", text, re.M), f"{name} still names the oci CLI"


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
        " oci_pods=0 oci_static_key_pods=0 policy_exceptions=0"
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

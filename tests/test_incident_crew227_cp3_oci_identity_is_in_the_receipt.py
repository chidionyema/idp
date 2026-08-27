"""crew#227 CP3, 2026-08-27: OKE workload identity for every pod that calls OCI was declined at
per-pod granularity because the estate runs a BASIC_CLUSTER (platform/oci/main.tf:13) and
per-pod OKE workload identity needs an Enhanced cluster, which Oracle bills per cluster hour
(CP3 recon comment on crew#227, 2026-08-25). The answer in place is the node's instance
principal via a dynamic group over the node pool (platform/oci/vault.tf), and every in-cluster
caller of the oci CLI (platform/state/cluster-state.yaml, platform/temporal/kini-state.yaml,
platform/observability/telemetry-coverage.yaml, platform/chaos/backstage-pod-kill.yaml) already
runs `oci --auth instance_principal`. Nothing proved that in the receipt: a pod could regress to
a static API key (env var or a Secret volume named for one) and no row would say so.

Rule: the receipt carries every container that calls OCI, its auth mode, and any static key it
still holds. Rung 4, incident test, both ways: a container using instance_principal with no key
is clean; a container that calls OCI with a static key env var, a static key Secret volume, or no
recognisable auth mode at all is named in the row.
"""
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _docs():
    return [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]


def _collect_src():
    docs = _docs()
    collect = next(d for d in docs if d["kind"] == "ConfigMap")["data"]["collect.py"]
    compile(collect, "collect.py", "exec")
    assert '"oci_identity": {' in collect
    return collect.split("spiffe = spiffe_rows()", 1)[1].split("at = datetime.now", 1)[0]


PODS = [
    # clean: calls oci via the CLI, explicit instance_principal, no static key anywhere.
    {"metadata": {"namespace": "backstage", "name": "cluster-state-clean"},
     "spec": {"containers": [{"name": "receipt", "image": "ghcr.io/oracle/oci-cli:20260826",
                               "command": ["/bin/sh", "-c"],
                               "args": ["oci --auth instance_principal os object put --bucket-name b"],
                               "env": []}],
              "volumes": []}},
    # regression: same image, but a static key env var is set alongside the CLI call.
    {"metadata": {"namespace": "backstage", "name": "cluster-state-static-env"},
     "spec": {"containers": [{"name": "receipt", "image": "ghcr.io/oracle/oci-cli:20260826",
                               "command": ["/bin/sh", "-c"],
                               "args": ["oci --auth instance_principal os object put --bucket-name b"],
                               "env": [{"name": "OCI_API_KEY", "value": "x"}]}],
              "volumes": []}},
    # regression: a Secret volume named for an OCI key is mounted into the OCI-calling container.
    {"metadata": {"namespace": "backstage", "name": "cluster-state-static-vol"},
     "spec": {"containers": [{"name": "receipt", "image": "ghcr.io/oracle/oci-cli:20260826",
                               "command": ["/bin/sh", "-c"], "args": ["oci os object put"],
                               "env": [], "volumeMounts": [{"name": "key", "mountPath": "/k"}]}],
              "volumes": [{"name": "key", "secret": {"secretName": "oci-api-key"}}]}},
    # regression: an SDK caller (env marks it as an OCI caller) with no recognised auth mode.
    {"metadata": {"namespace": "llm", "name": "sdk-caller"},
     "spec": {"containers": [{"name": "app", "image": "estate/app:1", "env":
                               [{"name": "OCI_CLI_AUTH", "value": "config_file"}]}],
              "volumes": []}},
    # not an OCI caller at all: must not appear in the row.
    {"metadata": {"namespace": "backstage", "name": "unrelated"},
     "spec": {"containers": [{"name": "web", "image": "estate/web:1", "env": []}], "volumes": []}},
]


def _run(pods):
    prog = f"import re, json\npods = {pods!r}\n" + _collect_src() + "\nprint(json.dumps({'oci_pods': oci_pods, 'static_key_pods': oci_static_key_pods, 'unknown_identity_pods': oci_unknown_identity_pods}))\n"
    out = subprocess.run([sys.executable, "-c", prog], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def test_receipt_names_oci_callers_their_identity_and_any_static_key():
    got = _run(PODS)
    by_pod = {r["pod"]: r for r in got["oci_pods"]}
    assert "backstage/unrelated" not in by_pod, "a container that never calls OCI must not be in the row"
    assert by_pod["backstage/cluster-state-clean"] == {
        "pod": "backstage/cluster-state-clean", "container": "receipt",
        "identity": "instance_principal", "static_key": []}
    assert by_pod["backstage/cluster-state-static-env"]["static_key"] == ["OCI_API_KEY"]
    # this container calls `oci` with no --auth flag at all: it is both a static-key regression
    # (the mounted Secret) and an unknown-identity one (no recognised auth mode in the call).
    assert by_pod["backstage/cluster-state-static-vol"]["static_key"] == ["key"]
    assert by_pod["backstage/cluster-state-static-vol"]["identity"] == "unknown"
    assert by_pod["llm/sdk-caller"]["identity"] == "unknown"
    assert got["static_key_pods"] == ["backstage/cluster-state-static-env", "backstage/cluster-state-static-vol"]
    assert got["unknown_identity_pods"] == ["backstage/cluster-state-static-vol", "llm/sdk-caller"]


def test_a_clean_cluster_has_no_static_key_and_no_unknown_identity():
    clean_only = [PODS[0], PODS[4]]
    got = _run(clean_only)
    assert len(got["oci_pods"]) == 1 and got["oci_pods"][0]["identity"] == "instance_principal"
    assert got["static_key_pods"] == [] and got["unknown_identity_pods"] == []

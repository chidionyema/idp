"""Founder, 2026-08-29: "can Otto use it?" -- K8sGPT had run for two days with nobody reading
its Result objects. The cluster-state receipt now carries them (kind, name, error, details) and
bin/idp-cluster-state prints them, so any reader -- a session, oke-check, Otto's dispatch runtime
-- gets the cluster's own diagnosis without a kube login. These tests keep that path whole."""
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "platform/state/cluster-state.yaml"


def _docs():
    return [d for d in yaml.safe_load_all(STATE.read_text()) if d]


def test_the_collector_may_list_k8sgpt_results():
    role = next(d for d in _docs() if d.get("kind") == "ClusterRole" and d["metadata"]["name"] == "cluster-state-reader")
    rule = next((r for r in role["rules"] if "core.k8sgpt.ai" in r["apiGroups"]), None)
    assert rule and "results" in rule["resources"] and {"get", "list"} <= set(rule["verbs"])


def test_the_receipt_carries_the_findings_and_the_head_counts_them():
    src = STATE.read_text()
    assert '/apis/core.k8sgpt.ai/v1alpha1/results' in src
    assert '"k8sgpt": k8sgpt' in src
    assert 'k8sgpt_findings={len(k8sgpt)}' in src
    assert 'list failed' in src.split("core.k8sgpt.ai/v1alpha1/results")[1][:600], "a failed list must be a row, never a zero"


def test_the_reader_prints_every_finding():
    src = (ROOT / "bin/idp-cluster-state").read_text()
    assert re.search(r'get\("k8sgpt"\)', src) and "k8sgpt     " in src


def test_otto_may_run_the_reader():
    # the runtime line lives inside a ConfigMap data string; grep is the honest read
    assert "Bash(bin/idp-cluster-state*)" in (ROOT / "platform/hermes-agent/estate.yaml").read_text()

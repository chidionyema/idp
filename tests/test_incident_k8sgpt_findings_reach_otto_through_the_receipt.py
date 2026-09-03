"""Founder, 2026-08-29: "can Otto use it?" -- K8sGPT had run for two days with nobody reading
its Result objects. The cluster-state receipt now carries them (kind, name, error, details) and
bin/idp-cluster-state prints them, so any reader -- a session, oke-check, Otto's dispatch runtime
-- gets the cluster's own diagnosis without a kube login. These tests keep that path whole."""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE = ROOT / "platform/state/cluster-state.yaml"


def _docs():
    return [d for d in yaml.safe_load_all(STATE.read_text()) if d]


def test_the_collector_may_list_k8sgpt_results():
    role = next(
        d
        for d in _docs()
        if d.get("kind") == "ClusterRole"
        and d["metadata"]["name"] == "cluster-state-reader"
    )
    rule = next((r for r in role["rules"] if "core.k8sgpt.ai" in r["apiGroups"]), None)
    assert (
        rule
        and "results" in rule["resources"]
        and {"get", "list"} <= set(rule["verbs"])
    )

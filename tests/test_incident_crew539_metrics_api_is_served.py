"""Incident test, crew#539 (2026-08-28): break-glass diagnose run 33140351385 printed
`error: Metrics API not available` for `kubectl top nodes` — no metrics-server on the estate
cluster, so live node usage could not be read during a P1 and the playbook fell back to allocated
requests. Rule: the tree carries a metrics-server row — the upstream kubernetes-sigs chart,
pinned, under Flux, admitted by the estate policy set (resources, a PriorityClass, restricted
profile) — and clusters/oke/platform.yaml reconciles it after the scheduling row."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROW = ROOT / "platform" / "metrics-server" / "metrics-server.yaml"
PLATFORM = ROOT / "clusters" / "oke" / "platform.yaml"


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_metrics_server_is_the_upstream_chart_pinned_and_admissible():
    docs = {d["kind"]: d for d in _docs(ROW)}
    hr = docs["HelmRelease"]
    chart = hr["spec"]["chart"]["spec"]
    assert chart["chart"] == "metrics-server" and chart["version"] == "3.14.0", "pinned upstream chart"
    assert docs["HelmRepository"]["spec"]["url"].startswith("https://kubernetes-sigs.github.io/metrics-server")
    values = hr["spec"]["values"]
    assert values["priorityClassName"] == "system-cluster-critical", "require-priority-class; infrastructure-critical is the radio room only"
    assert values["resources"]["limits"]["cpu"] and values["resources"]["limits"]["memory"], "require-pod-requests-limits"
    assert docs["Namespace"]["metadata"]["labels"]["app.kubernetes.io/part-of"] == "idp"
    assert docs["Namespace"]["metadata"]["name"] == "metrics-server", "disallow-default-namespace"
    assert hr["spec"]["install"]["remediation"]["retries"] >= 1


def test_cluster_reconciles_metrics_server_after_scheduling_with_a_health_check():
    rows = {d["metadata"]["name"]: d for d in _docs(PLATFORM) if d.get("kind") == "Kustomization"}
    row = rows["metrics-server"]
    assert row["spec"]["path"] == "./platform/metrics-server"
    assert {"name": "scheduling"} in row["spec"]["dependsOn"], "the PriorityClass exists before a pod names it"
    assert row["spec"]["wait"] is True
    hc = row["spec"]["healthChecks"][0]
    assert (hc["kind"], hc["name"], hc["namespace"]) == ("Deployment", "metrics-server", "metrics-server")

"""
Incident test (rung 4), crew#645 CP5. Founder, 2026-08-29 19:0xZ: "i need all metrics exposed
... on backstage ... always ... numbers for everything we collect", then his Backstage
Visibility Plan (wire the Prometheus and Kubernetes plugins, annotate the catalogue, put the
numbers on the entity pages).

Measured before the change: 440 catalogue entities, 0 with a kubernetes annotation, so the
Kubernetes tab shipped in crew#412 rendered nothing; no Prometheus plugin at all. Five things
must stay true, and this file refuses a checkout where any one is false:

  1. every cluster entity the generator renders (Flux row or Helm chart with a namespace)
     carries the Kubernetes plugin's namespace + label-selector annotations and the
     Prometheus plugin's rule, alert and labels annotations;
  2. every rule name the generator writes exists as a recording rule in
     platform/monitoring/rules/capacity.yaml, and that file is in the rules kustomization;
  3. the container config points the Prometheus proxy at the estate's own Prometheus,
     GET only, and the Kubernetes plugin no longer skips the metrics lookup;
  4. the portal app registers the metrics plugin.

The rendered catalogue itself is not in git (catalog/catalog-info.yaml is generated on the way
to the cluster by bin/idp-catalog-push), so 1 grades the generator on the fixture inventory.
"""

import os
import pathlib
import re
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"
RULES = ROOT / "platform/monitoring/rules"
K8S = ("backstage.io/kubernetes-namespace", "backstage.io/kubernetes-label-selector")
PROM = ("prometheus.io/rule", "prometheus.io/alert", "prometheus.io/labels")


def _render(tmp_path):
    out = tmp_path / "out"
    env = {
        **os.environ,
        "INV": str(ROOT / "tests/fixtures/inventory.json"),
        "OUT": str(out),
    }
    subprocess.run([str(GEN)], check=True, env=env, capture_output=True, text=True)
    return [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]


def _cluster(entities):
    return [
        e
        for e in entities
        if (e.get("metadata", {}).get("annotations") or {}).get("estate/source")
        == "cluster"
        and e["spec"]["type"] in ("flux-row", "helm-chart")
    ]


def _records():
    doc = yaml.safe_load((RULES / "capacity.yaml").read_text())
    return {
        r["record"] for g in doc["spec"]["groups"] for r in g["rules"] if "record" in r
    }


def test_every_helm_chart_entity_shows_its_numbers(tmp_path):
    charts = [
        e for e in _cluster(_render(tmp_path)) if e["spec"]["type"] == "helm-chart"
    ]
    assert charts, "no Helm chart entity rendered"
    for e in charts:
        ann = e["metadata"]["annotations"]
        missing = [k for k in K8S + PROM if k not in ann]
        assert not missing, f"{e['metadata']['name']}: missing {missing}"
        assert ann["backstage.io/kubernetes-namespace"] == ann["estate/namespace"]
        assert (
            ann["backstage.io/kubernetes-label-selector"]
            == f"app.kubernetes.io/instance={ann['estate/flux-name']}"
        )
        assert ann["prometheus.io/labels"] == f"namespace={ann['estate/namespace']}"


def test_a_flux_row_that_owns_a_namespace_shows_its_numbers(tmp_path):
    rows = [e for e in _cluster(_render(tmp_path)) if e["spec"]["type"] == "flux-row"]
    with_ns = [
        e
        for e in rows
        if "backstage.io/kubernetes-namespace" in e["metadata"]["annotations"]
    ]
    assert with_ns, "no Flux row rendered with a namespace"
    for e in with_ns:
        ann = e["metadata"]["annotations"]
        assert all(k in ann for k in PROM), e["metadata"]["name"]
        assert (
            ann["backstage.io/kubernetes-label-selector"]
            == f"kustomize.toolkit.fluxcd.io/name={ann['estate/flux-name']}"
        )


def test_every_rule_the_catalogue_names_is_a_recording_rule(tmp_path):
    records = _records()
    named = set()
    for e in _cluster(_render(tmp_path)):
        rule = e["metadata"]["annotations"].get("prometheus.io/rule", "")
        for part in filter(None, rule.split(",")):
            query, _, dim = part.partition("|")
            assert dim == "pod", part
            named.add(re.sub(r"\{.*\}$", "", query))
    assert named and named <= records, (
        f"named in the catalogue but not recorded: {named - records}"
    )
    kz = yaml.safe_load((RULES / "kustomization.yaml").read_text())
    assert "capacity.yaml" in kz["resources"]
    alerts = {
        r["alert"]
        for g in yaml.safe_load((RULES / "capacity.yaml").read_text())["spec"]["groups"]
        for r in g["rules"]
        if "alert" in r
    }
    assert "RequestBelowMeasuredPeak" in alerts


def test_the_portal_reads_the_estates_own_prometheus_read_only():
    cfg = yaml.safe_load((ROOT / "backstage/app-config.container.yaml").read_text())
    ep = cfg["proxy"]["endpoints"]["/prometheus/api"]
    assert ep["target"] == "http://kps-prometheus.monitoring.svc:9090/api/v1/"
    assert ep["allowedMethods"] == ["GET"]
    assert "credentials" not in ep, (
        "the Prometheus proxy must require the signed-in user's token"
    )
    cluster = cfg["kubernetes"]["clusterLocatorMethods"][0]["clusters"][0]
    assert cluster["skipMetricsLookup"] is False


def test_the_portal_app_registers_the_metrics_plugin():
    app = (ROOT / "backstage/packages/app/src/App.tsx").read_text()
    assert "metricsPlugin" in app
    mod = (ROOT / "backstage/packages/app/src/modules/metrics/index.tsx").read_text()
    assert "convertLegacyPlugin(backstagePluginPrometheusPlugin" in mod
    assert "isPrometheusAvailable" in mod
    pkg = yaml.safe_load((ROOT / "backstage/packages/app/package.json").read_text())
    assert "@roadiehq/backstage-plugin-prometheus" in pkg["dependencies"]
    assert "@backstage/core-compat-api" in pkg["dependencies"]

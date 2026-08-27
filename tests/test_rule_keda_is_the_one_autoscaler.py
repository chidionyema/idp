"""Rule (crew#488 CP7, rung 2: one property over every manifest, not one example per file):
the estate has one autoscaler, KEDA, installed once in platform/keda, pinned, and exporting to the
one collector (LAW 50). Any other scale-to-zero mechanism under platform/ (Knative Serving, a
second KEDA, a cron that sets replicas) is the stitching the headline forbids and fails here."""
from __future__ import annotations

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLATFORM = ROOT / "platform"
COLLECTOR = "signoz-otel-collector.observability.svc:4317"


def _docs():
    for path in sorted(PLATFORM.rglob("*.yaml")):
        text = path.read_text(errors="ignore")
        try:
            for doc in yaml.safe_load_all(text):
                if isinstance(doc, dict):
                    yield path, doc
        except yaml.YAMLError:
            # Flux postBuild `${…}` substitutions are legal YAML; a file that is not parses nowhere
            # else either and has its own gate. This rule judges kinds, not syntax.
            continue


def test_keda_is_installed_once_pinned_and_emitting():
    releases = {(p, d["metadata"]["name"]): d for p, d in _docs()
                if d.get("kind") == "HelmRelease" and str(d["spec"]["chart"]["spec"].get("chart", "")).startswith("keda")}
    names = sorted(n for _, n in releases)
    assert names == ["keda", "keda-add-ons-http"], names
    for (path, name), d in releases.items():
        assert path.parent == PLATFORM / "keda", f"{name} lives in {path}, not platform/keda"
        version = str(d["spec"]["chart"]["spec"].get("version", ""))
        assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"{name} chart version not pinned: {version!r}"
    core = releases[(PLATFORM / "keda" / "keda.yaml", "keda")]["spec"]["values"]
    assert core["opentelemetry"]["collector"]["uri"] == COLLECTOR
    assert core["opentelemetry"]["operator"]["enabled"] is True


def test_no_second_autoscaler_under_platform():
    forbidden_kinds = {"KnativeServing", "Service.serving.knative.dev", "Configuration.serving.knative.dev"}
    forbidden_charts = ("knative", "openfaas", "fission")
    hits = []
    for path, d in _docs():
        kind = d.get("kind", "")
        api = d.get("apiVersion", "")
        if kind in forbidden_kinds or api.startswith("serving.knative.dev") or api.startswith("operator.knative.dev"):
            hits.append(f"{path.relative_to(ROOT)}: {kind}")
        if kind == "HelmRelease":
            chart = str(d["spec"]["chart"]["spec"].get("chart", ""))
            if chart.startswith(forbidden_charts):
                hits.append(f"{path.relative_to(ROOT)}: chart {chart}")
        if kind == "CronJob" and "scale" in yaml.safe_dump(d.get("spec", {})) and "replicas" in yaml.safe_dump(d.get("spec", {})):
            hits.append(f"{path.relative_to(ROOT)}: CronJob that sets replicas")
    assert hits == [], hits


def test_flux_row_waits_on_both_releases():
    rows = [d for d in yaml.safe_load_all((ROOT / "clusters/oke/platform.yaml").read_text())
            if isinstance(d, dict) and d.get("metadata", {}).get("name") == "keda"]
    assert len(rows) == 1
    checks = {(h["name"], h["namespace"]) for h in rows[0]["spec"]["healthChecks"]}
    assert checks == {("keda", "keda"), ("keda-add-ons-http", "keda")}
    assert rows[0]["spec"]["path"] == "./platform/keda"

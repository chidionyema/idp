"""Incident test, crew#392 (2026-08-27): mcp-agentgateway and mcp-github emit their own spans to the
collector, and telemetry-coverage still listed both pods as never seen (oke-check 33065950588,
pods_seen=0). Two causes, one rule: a pod the backend holds in any signal counts as seen, and the
collector stamps the pod identity on what it receives so a self-emitting workload has one.
Rung 4: the coverage query reads the traces table (both ways: a traces-only pod is seen; a pod in
no table is still missing), and the SigNoz values put k8sattributes ahead of the traces and logs
exporters while the receivers the chart ships stay in place.
"""
import shutil
import subprocess
import sys
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "platform" / "observability"
NOW = datetime(2026, 8, 27, 11, 0, tzinfo=timezone.utc)


def _collector() -> types.ModuleType:
    docs = [d for d in yaml.safe_load_all((OBS / "telemetry-coverage.yaml").read_text()) if d]
    cm = next(d for d in docs if d["kind"] == "ConfigMap")
    mod = types.ModuleType("collect")
    exec(compile(cm["data"]["collect.py"], "collect.py", "exec"), mod.__dict__)
    return mod


def _pod(ns, name):
    start = (NOW - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"metadata": {"namespace": ns, "name": name}, "status": {"phase": "Running", "startTime": start}}


def test_incident_crew392_a_pod_seen_only_in_traces_counts_and_an_unseen_pod_still_fails():
    mod = _collector()
    pods = {"items": [_pod("mcp", "agentgateway-1"), _pod("mcp", "github-mcp-1")]}
    assert "traces" in mod.QUERIES and "signoz_traces" in mod.QUERIES["traces"]

    def traces_only(sql):
        return {("mcp", "agentgateway-1")} if "signoz_traces" in sql else set()

    head, body = mod.main(kube=lambda _: pods, clickhouse=traces_only, now=NOW)
    assert head.startswith("FAIL telemetry-coverage") and "seen=1 missing=1" in head, head
    assert body["missing"] == [{"ns": "mcp", "pod": "github-mcp-1"}], "the pod in no table is still missing"

    def both(sql):
        if "hubble" in sql:   # crew#539 CP12: the receipt also needs a radio-room flow count > 0
            return {("4",)}
        return {("mcp", "agentgateway-1"), ("mcp", "github-mcp-1")} if "signoz_traces" in sql else set()

    head, _ = mod.main(kube=lambda _: pods, clickhouse=both, now=NOW)
    assert head.startswith("ok telemetry-coverage") and "missing=0" in head, head


def test_incident_crew392_collector_stamps_the_pod_on_traces_and_logs():
    values = yaml.safe_load((OBS / "values.yaml").read_text())
    cfg = values["otelCollector"]["config"]
    assert cfg["processors"]["k8sattributes"]["pod_association"] == [{"sources": [{"from": "connection"}]}]
    pipelines = cfg["service"]["pipelines"]
    for name in ("traces", "logs"):
        assert pipelines[name]["processors"][0] == "k8sattributes", name
        assert "receivers" not in pipelines[name], "receivers are the chart's; a list here would replace them"
    assert "metrics" not in pipelines, "metrics arrive through the agent and keep the shipped pipeline"


def test_incident_crew392_rendered_chart_keeps_the_shipped_receivers():
    """Helm replaces lists, so the override must keep the otlp receiver the workloads send to."""
    if not shutil.which("helm"):
        pytest.skip("helm not installed")
    hr = next(d for d in yaml.safe_load_all((OBS / "signoz.yaml").read_text())
              if d and d["kind"] == "HelmRelease")
    version = hr["spec"]["chart"]["spec"]["version"]
    subprocess.run(["helm", "repo", "add", "signoz", "https://charts.signoz.io"], capture_output=True)
    r = subprocess.run(["helm", "template", "signoz", "signoz/signoz", "--version", version,
                        "-f", str(OBS / "values.yaml"), "--show-only", "templates/otel-collector/configmap.yaml"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"chart not fetchable here: {r.stderr[-200:]}")
    cm = yaml.safe_load(r.stdout)
    conf = yaml.safe_load(next(v for k, v in cm["data"].items() if k.endswith(".yaml")))
    traces = conf["service"]["pipelines"]["traces"]
    assert traces["processors"][0] == "k8sattributes" and "otlp" in traces["receivers"], traces
    assert "k8sattributes" in conf["processors"]
    sys.stdout.write(f"rendered traces pipeline: {traces}\n")

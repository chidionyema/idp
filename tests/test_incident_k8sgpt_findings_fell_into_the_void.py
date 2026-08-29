"""Founder, 2026-08-29: "why install anything if we don't use it ... it just fell into the void".
K8sGPT had run for two days with serviceMonitor.enabled false and no rule on its metrics, so
every finding was written and never read (LAW 28). These keep the read path wired."""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(p):
    return [d for d in yaml.safe_load_all((ROOT / p).read_text()) if d]


def test_the_operator_exposes_its_metrics_to_prometheus():
    hr = next(d for d in _docs("platform/healing/k8sgpt.yaml") if d["kind"] == "HelmRelease")
    assert hr["spec"]["values"]["serviceMonitor"]["enabled"] is True


def test_findings_and_blindness_both_page():
    rule = next(d for d in _docs("platform/monitoring/rules/k8sgpt.yaml") if d["kind"] == "PrometheusRule")
    alerts = {r["alert"]: r for g in rule["spec"]["groups"] for r in g["rules"]}
    assert "k8sgpt_number_of_results_by_type" in alerts["K8sGPTFinding"]["expr"]
    assert "absent(k8sgpt_number_of_results)" in alerts["K8sGPTBlind"]["expr"]
    assert "k8sgpt_number_of_failed_backend_ai_calls" in alerts["K8sGPTBlind"]["expr"]
    assert "k8sgpt.yaml" in (ROOT / "platform/monitoring/rules/kustomization.yaml").read_text()


def test_every_analyser_installed_has_a_rule_that_reads_it():
    """LAW 28 as a fence: a K8sGPT object in platform/ without a PrometheusRule naming its metrics."""
    crs = [f for f in (ROOT / "platform").rglob("*.yaml") if any(d.get("kind") == "K8sGPT" for d in _docs(f))]
    assert crs, "no analyser found"
    rules = "".join(f.read_text() for f in (ROOT / "platform/monitoring/rules").glob("*.yaml"))
    assert "k8sgpt_number_of_results" in rules

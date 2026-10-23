"""The research engine's alerts (idp#6908) are wired to Jobs that exist and can fail."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "platform" / "monitoring" / "rules"
ENGINE = ROOT / "platform" / "research-engine"


def _docs(path):
    with open(path) as f:
        return [d for d in yaml.safe_load_all(f) if d]


def _alerts():
    (rule,) = _docs(RULES / "research-engine.yaml")
    assert rule["kind"] == "PrometheusRule"
    (group,) = rule["spec"]["groups"]
    assert group["name"] == "estate.research-engine"
    return {a["alert"]: a for a in group["rules"]}


def test_both_alerts_exist_with_annotations():
    alerts = _alerts()
    assert set(alerts) == {"ResearchEngineJobFailed", "ResearchExaUnusable"}
    for a in alerts.values():
        assert a["annotations"]["summary"]
        assert a["annotations"]["description"]
        assert a["labels"]["severity"]


def test_alerts_grade_exhausted_jobs_not_retried_pods():
    # kube_job_status_failed counts failed pods, so a recovered first attempt would page.
    for a in _alerts().values():
        assert a["expr"].startswith("kube_job_failed{")
        assert 'condition="true"' in a["expr"]
        assert 'namespace="research"' in a["expr"]


def test_rules_file_is_in_the_kustomization():
    (k,) = _docs(RULES / "kustomization.yaml")
    assert "research-engine.yaml" in k["resources"]


def test_each_alert_names_a_cronjob_that_is_deployed():
    (k,) = _docs(ENGINE / "kustomization.yaml")
    cronjobs = {
        d["metadata"]["name"]
        for f in k["resources"]
        if f.endswith(".yaml")
        for d in _docs(ENGINE / f)
        if d.get("kind") == "CronJob"
    }
    assert {"research-engine", "exa-credit-probe"} <= cronjobs
    alerts = _alerts()
    assert '"research-engine-.*"' in alerts["ResearchEngineJobFailed"]["expr"]
    assert '"exa-credit-probe-.*"' in alerts["ResearchExaUnusable"]["expr"]


def test_probe_reads_the_engine_key_from_a_file():
    docs = {d["kind"]: d for d in _docs(ENGINE / "exa-credit-probe.yaml")}
    spec = docs["CronJob"]["spec"]["jobTemplate"]["spec"]["template"]["spec"]
    (c,) = spec["containers"]
    assert "env" not in c and "envFrom" not in c  # Kyverno refuses secrets in env
    secrets = {v["secret"]["secretName"] for v in spec["volumes"] if "secret" in v}
    assert secrets == {"human-exa"}
    assert "/secrets/exa/EXA_API_KEY" in docs["ConfigMap"]["data"]["probe.py"]

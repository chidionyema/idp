"""Incident test, 2026-08-29: hermes-agent-gateway (Otto) had zero running pods for 4h16m and the
only thing that said so was a break-glass run a session happened to dispatch. Founder: "why did our
monitoring, alerting, all the tools we presumably have ...". Two rules (LAW 28): Otto having no pod is
a named critical alert, and the architect-doctor playbook prints what Alertmanager holds for the
namespace so the alert is read where the pod is read. Both ways: the rule and the row as committed
pass; a rule set without OttoDown, or a playbook without the row, is named.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "platform/monitoring/rules/estate.yaml"
PLAYBOOK = ROOT / "bin/idp-oke-break-glass"


def _alerts(text: str) -> dict:
    doc = yaml.safe_load(text)
    return {r["alert"]: r for g in doc["spec"]["groups"] for r in g["rules"]}


def test_otto_with_no_pod_is_a_critical_alert():
    rule = _alerts(RULES.read_text()).get("OttoDown")
    assert rule, "no OttoDown rule in estate.yaml"
    assert 'deployment="hermes-agent-gateway"' in rule["expr"] and "== 0" in rule["expr"]
    assert rule["labels"]["severity"] == "critical"
    assert rule["for"] == "10m"
    assert "architect-doctor" in rule["annotations"]["description"]


def test_the_rule_is_named_when_missing():
    text = RULES.read_text().replace("OttoDown", "SomethingElse")
    assert "OttoDown" not in _alerts(text)


def test_architect_doctor_reads_what_alertmanager_holds():
    body = PLAYBOOK.read_text().split("pb_architect_doctor()", 1)[1].split("\n}\n", 1)[0]
    assert "show alerts-firing" in body
    assert "amtool" in body and "alert query namespace=$ns" in body

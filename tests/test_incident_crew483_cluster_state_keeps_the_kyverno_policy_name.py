"""Incident test, crew#483 (2026-08-27): oke-check 33063811930 showed HelmRelease observability/k8s-infra
Failed with the message cut at 'admission webhook "validate.kyverno.svc-fail" denied the request:'.
The collector kept 300 characters of every Flux Ready message, and Kyverno writes the policy and
rule names after that colon, so the receipt named a refusal without the policy. Rule: a Flux message
reaches the receipt whole up to 2000 characters, and a longer one keeps its tail, where the policy is.
Rung 4, both ways: a short message is untouched; a 2300-character denial keeps its policy name.
"""
import ast
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "platform/state/cluster-state.yaml"


def _flux_message():
    docs = [d for d in yaml.safe_load_all(MANIFEST.read_text()) if d]
    src = next(d["data"]["collect.py"] for d in docs if d.get("kind") == "ConfigMap" and "collect.py" in d.get("data", {}))
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "flux_message")
    ns: dict = {}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "collect.py", "exec"), ns)
    return ns["flux_message"]


def test_incident_crew483_a_kyverno_denial_keeps_its_policy_name():
    fm = _flux_message()
    head = ('Helm install failed for release observability-agent/observability-agent-k8s-infra with chart '
            'k8s-infra@0.17.0: server-side apply failed for object observability-agent/observability-agent-'
            'k8s-infra-otel-agent apps/v1, Kind=DaemonSet: admission webhook "validate.kyverno.svc-fail" '
            'denied the request: \n\nresource DaemonSet/observability-agent/observability-agent-k8s-infra-'
            'otel-agent was blocked due to the following policies \n\n')
    policy = "require-pod-probes:\n  autogen-check-probes: validation error: liveness and readiness probes are required"
    assert len(head) > 300
    assert policy in fm(head + policy)
    assert policy in fm(head + ("x" * 1800) + policy), "past 2000 the tail with the policy survives"


def test_incident_crew483_a_short_message_is_untouched():
    fm = _flux_message()
    assert fm("Applied revision: main@sha1:abc") == "Applied revision: main@sha1:abc"

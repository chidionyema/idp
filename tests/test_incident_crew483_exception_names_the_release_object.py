"""Incident 2026-08-27 (crew#483): idp#309 waived disallow-host-path for `k8s-infra-otel-agent*`,
but helm-controller names a release "[targetNamespace-]name" (HelmRelease API, spec.releaseName
default) and the chart prefixes every object with it, so the live DaemonSet was
observability-agent-k8s-infra-otel-agent and Kyverno kept refusing it. The render gate and the
crew#388 test both templated with the bare name and passed. Rule (rung 4): a PolicyException that
matches on names must match the name helm-controller will produce for the release it excuses.
"""
import fnmatch
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def helm_controller_release_name(hr):
    spec = hr["spec"]
    if spec.get("releaseName"):
        return spec["releaseName"]
    tns = spec.get("targetNamespace")
    return f"{tns}-{hr['metadata']['name']}" if tns else hr["metadata"]["name"]


def _matches(exception, ns, name):
    for m in exception["spec"]["match"]["any"]:
        r = m["resources"]
        if ns in r.get("namespaces", [ns]) and any(fnmatch.fnmatch(name, g) for g in r.get("names", ["*"])):
            return True
    return False


def test_incident_crew483_k8s_infra_exception_matches_the_live_daemonset():
    hr = next(d for d in _docs(ROOT / "platform/observability/k8s-infra.yaml") if d["kind"] == "HelmRelease")
    exc = next(d for d in _docs(ROOT / "platform/edge/k8s-infra-exception.yaml") if d["kind"] == "PolicyException")
    release = helm_controller_release_name(hr)
    ns = hr["spec"].get("targetNamespace") or hr["metadata"]["namespace"]
    live = f"{release}-otel-agent"  # the k8s-infra chart's node-agent DaemonSet: <release>-otel-agent
    assert _matches(exc, ns, live), f"exception never matches {ns}/{live}"


def test_incident_crew483_release_name_rule_both_ways():
    base = {"metadata": {"name": "k8s-infra", "namespace": "observability"}, "spec": {}}
    assert helm_controller_release_name(base) == "k8s-infra"
    assert helm_controller_release_name({**base, "spec": {"targetNamespace": "observability-agent"}}) == "observability-agent-k8s-infra"
    assert helm_controller_release_name({**base, "spec": {"targetNamespace": "observability-agent", "releaseName": "pinned"}}) == "pinned"
    exc = {"spec": {"match": {"any": [{"resources": {"namespaces": ["observability-agent"], "names": ["k8s-infra-otel-agent*"]}}]}}}
    assert _matches(exc, "observability-agent", "k8s-infra-otel-agent")
    assert not _matches(exc, "observability-agent", "observability-agent-k8s-infra-otel-agent"), "main's exception must fail this"

"""Incident 2026-08-26 (crew#325): cert-manager ran zero pods on OKE for 41 hours and the
langfuse HelmRelease stayed refused for 2.5 hours. Two causes, both Kyverno:

* require-requests-limits refused every cert-manager pod (requests set, no limits), and
  require-pod-probes refused cainjector, the one container the chart renders without a probe.
* the langfuse PolicyException was created in `observability`, but Kyverno runs with
  --exceptionNamespace=kyverno (platform/edge/kyverno.yaml) and ignores every other namespace.

Rules, not code: every cert-manager component carries limits, and every PolicyException in
platform/ lives in the one namespace Kyverno reads. Rung 4 (incident test)."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _docs(rel: str) -> list[dict]:
    return [d for d in yaml.safe_load_all((ROOT / rel).read_text()) if d]


def test_incident_crew325_cert_manager_components_carry_limits() -> None:
    hr = next(d for d in _docs("platform/edge/cert-manager.yaml") if d["kind"] == "HelmRelease")
    v = hr["spec"]["values"]
    for component in (v, v["webhook"], v["cainjector"], v["startupapicheck"]):
        limits = component["resources"]["limits"]
        assert set(limits) == {"cpu", "memory"}, component


def test_incident_crew325_cainjector_has_a_probe_exception() -> None:
    exc = next(d for d in _docs("platform/edge/cert-manager.yaml") if d["kind"] == "PolicyException")
    assert exc["metadata"]["namespace"] == "kyverno"
    assert [e["policyName"] for e in exc["spec"]["exceptions"]] == ["require-pod-probes"]
    assert exc["spec"]["match"]["any"][0]["resources"]["names"] == ["cert-manager-cainjector*"]


def test_incident_crew325_every_policy_exception_lives_where_kyverno_reads() -> None:
    kyverno = next(d for d in _docs("platform/edge/kyverno.yaml") if d["kind"] == "HelmRelease")
    exceptions = kyverno["spec"]["values"]["features"]["policyExceptions"]
    assert exceptions == {"enabled": True, "namespace": "kyverno"}
    found = 0
    for f in ROOT.glob("platform/**/*.yaml"):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "PolicyException":
                found += 1
                assert d["metadata"].get("namespace") == "kyverno", f
    assert found >= 3

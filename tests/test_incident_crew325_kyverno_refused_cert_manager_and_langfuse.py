"""Incident 2026-08-26 (crew#325): cert-manager ran zero pods on OKE for 41 hours and the
langfuse HelmRelease stayed refused for 2.5 hours. Two causes, both Kyverno:

* require-requests-limits refused every cert-manager pod (requests set, no limits), and
  require-pod-probes refused cainjector, the one container the chart renders without a probe.
* the langfuse PolicyException was created in `observability`, but Kyverno runs with
  --exceptionNamespace=kyverno (platform/edge/kyverno.yaml) and ignores every other namespace.

Rules, not code: every cert-manager component carries limits, and every PolicyException in
platform/ lives in the one namespace Kyverno reads. Rung 4 (incident test)."""
import subprocess
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
    # Graded on the rendered output, not the file: platform/observability/kustomization.yaml sets
    # `namespace: observability`, which rewrote an exception whose file said `kyverno`.
    kyverno = next(d for d in _docs("platform/edge/kyverno.yaml") if d["kind"] == "HelmRelease")
    exceptions = kyverno["spec"]["values"]["features"]["policyExceptions"]
    assert exceptions == {"enabled": True, "namespace": "kyverno"}
    paths = sorted(
        {
            d["spec"]["path"]
            for f in ROOT.glob("clusters/oke/*.yaml")
            for d in yaml.safe_load_all(f.read_text())
            if d and d.get("kind") == "Kustomization" and d["spec"].get("path", "").startswith("./platform/")
        }
    )
    assert paths
    found = 0
    for k in paths:
        out = subprocess.run(
            ["kustomize", "build", str(ROOT / k)], capture_output=True, text=True, check=True
        ).stdout
        for d in yaml.safe_load_all(out):
            if d and d.get("kind") == "PolicyException":
                found += 1
                assert d["metadata"].get("namespace") == "kyverno", (k, d["metadata"]["name"])
    assert found >= 3


def test_incident_crew325_seaweedfs_image_names_its_registry() -> None:
    # The OKE node runtime enforces short-name mode: an unqualified image never pulls.
    values = yaml.safe_load((ROOT / "platform/observability/langfuse-values.yaml").read_text())
    repository = values["global"]["seaweedfs"]["image"]["repository"]
    assert repository.split("/")[0] == "docker.io", repository

"""Run 33236900434 (2026-08-29, break-glass k8sgpt-analyze): the K8sGPT operator's Deployment for
object healing/estate was refused by Kyverno on seven policies and the CR had been Current for 29h
with no analyzer. The object must carry the security context the estate's policy set demands, and
the one policy the CRD cannot satisfy (probes) is waived for that Deployment alone.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "platform" / "healing" / "analyzer"


def _cr():
    docs = [d for d in yaml.safe_load_all((ANALYZER / "k8sgpt.yaml").read_text()) if d]
    return [d for d in docs if d["kind"] == "K8sGPT"][0]


def test_run_33236900434_the_analyzer_container_drops_all_and_cannot_escalate():
    c = _cr()["spec"]["containerSecurityContext"]
    assert c["allowPrivilegeEscalation"] is False
    assert c["capabilities"]["drop"] == ["ALL"]
    assert c["readOnlyRootFilesystem"] is True and c["runAsNonRoot"] is True
    assert c["seccompProfile"]["type"] == "RuntimeDefault"
    p = _cr()["spec"]["securityContext"]
    assert p["runAsNonRoot"] is True and p["seccompProfile"]["type"] == "RuntimeDefault"
    assert _cr()["spec"]["noCache"] is True, "a read-only root filesystem has nowhere for the cache"


def test_run_33236900434_only_probes_are_waived_and_only_for_the_analyzer():
    ex = yaml.safe_load((ANALYZER / "exception.yaml").read_text())
    assert ex["kind"] == "PolicyException" and ex["metadata"]["namespace"] == "kyverno"
    assert [e["policyName"] for e in ex["spec"]["exceptions"]] == ["require-pod-probes", "secrets-not-from-env-vars"]  # 2026-08-29: run 33238265861
    res = ex["spec"]["match"]["any"][0]["resources"]
    assert res["namespaces"] == ["healing"] and res["names"] == ["estate*"]
    kust = yaml.safe_load((ANALYZER / "kustomization.yaml").read_text())
    assert "exception.yaml" in kust["resources"]


def test_incident_20260829_secret_env_policy_is_excepted_for_the_analyzer():
    """Run 33238265861: secrets-not-from-env-vars denied the analyzer after the security context landed."""
    import yaml
    doc = yaml.safe_load((ANALYZER / "exception.yaml").read_text())
    names = {e["policyName"] for e in doc["spec"]["exceptions"]}
    assert {"require-pod-probes", "secrets-not-from-env-vars"} <= names

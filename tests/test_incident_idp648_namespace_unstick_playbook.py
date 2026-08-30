"""idp#648 (2026-08-29): the backstage Namespace moved between Flux rows, the old prune:true row
garbage-collected it, and it sat Terminating for 16+ min with the catalogue 404 (oke-check run
33226089358). Three fences, one incident: the namespace can never be pruned again; diagnose
prints why a namespace is Terminating; a named playbook clears what holds it."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_diagnose_prints_k8sgpt_findings_first():
    src = (ROOT / "bin/idp-oke-break-glass").read_text()
    body = src[src.index("pb_diagnose()") : src.index("\npb_", src.index("pb_diagnose()") + 1)]
    assert body.index("k8sgpt-results") < body.index("show nodes")


def test_every_platform_namespace_object_is_never_pruned():
    bad = []
    for f in ROOT.glob("platform/*/namespace/base/namespace.yaml"):
        for doc in yaml.safe_load_all(f.read_text()):
            if doc and doc.get("kind") == "Namespace":
                labels = (doc.get("metadata") or {}).get("labels") or {}
                if labels.get("kustomize.toolkit.fluxcd.io/prune") != "disabled":
                    bad.append(str(f.relative_to(ROOT)))
    assert not bad, f"a Namespace that moves rows gets pruned by the old row: {bad}"


def test_provider_independence_never_judges_a_delete():
    """Run 33227815539: no-provider-storage-class denied the DELETE of the old PVC, so the namespace
    could never finish terminating. A portability rule has nothing to say about a DELETE."""
    for doc in yaml.safe_load_all((ROOT / "platform/edge/provider-independence.yaml").read_text()):
        if not doc or doc.get("kind") not in ("ClusterPolicy", "ValidatingPolicy"):
            continue
        for rule in doc["spec"].get("rules", []):
            for m in (rule.get("match") or {}).get("any", []):
                ops = (m.get("resources") or {}).get("operations")
                assert ops and "DELETE" not in ops, f"{rule['name']} matches DELETE"


def test_diagnose_prints_every_admission_denial_whole():
    """Run 33239797940: `kubectl get events` cut the Kyverno denial to `denied the request: ...`, so
    the run could not name the rule. The playbook now prints each FailedCreate message in full."""
    src = (ROOT / "bin/idp-oke-break-glass").read_text()
    assert "healing-denials" in src
    row = src[src.index("healing-denials") : src.index("\n", src.index("healing-denials"))]
    assert "reason=FailedCreate" in row and "{.message}" in row
    assert "tail -c" in row, "the message is bounded, not cut per line"

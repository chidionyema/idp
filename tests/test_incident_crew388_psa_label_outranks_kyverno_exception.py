"""Incident 2026-08-27 (crew#388, crew#320): the k8s-infra otel-agent DaemonSet sat InProgress
for a day with a Kyverno PolicyException that waived disallow-host-path, because the refusal was
the Pod Security Admission label on namespace observability (`enforce: restricted`), which no
Kyverno exception can waive. cluster-state events_warning carried the exact message; nobody
had read it (idp#286 added the row).

Rule (rung 4, incident test, repo-wide): every PolicyException that waives a hostPath rule
names only namespaces whose Namespace manifest carries `pod-security.kubernetes.io/enforce:
privileged`. restricted and baseline both forbid hostPath, so a waiver into either is a
DaemonSet that never schedules. Proved both ways: the checkout passes; the same exception
pointed at a restricted namespace is refused.
"""
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOSTPATH_POLICIES = {"disallow-host-path", "restrict-volume-types"}
ENFORCE = "pod-security.kubernetes.io/enforce"


def _docs(path):
    try:
        return [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
    except yaml.YAMLError:
        return []


def namespaces_enforce(root=ROOT / "platform"):
    out = {}
    for f in sorted(root.rglob("*.yaml")):
        for d in _docs(f):
            if d.get("kind") == "Namespace":
                out[d["metadata"]["name"]] = (d["metadata"].get("labels") or {}).get(ENFORCE, "privileged")
    return out


def hostpath_waivers(root=ROOT / "platform"):
    for f in sorted(root.rglob("*.yaml")):
        for d in _docs(f):
            if d.get("kind") != "PolicyException":
                continue
            waived = {e.get("policyName") for e in d["spec"].get("exceptions", [])}
            if not waived & HOSTPATH_POLICIES:
                continue
            for block in d["spec"]["match"].get("any", []) + d["spec"]["match"].get("all", []):
                for ns in block.get("resources", {}).get("namespaces", []):
                    yield f.relative_to(root), d["metadata"]["name"], ns


def violations(root=ROOT / "platform"):
    # A namespace with no manifest here (spire-server, created by its chart) carries no PSA label,
    # and an unlabelled namespace admits everything; only a manifest that sets the level can refuse.
    levels = namespaces_enforce(root)
    return [f"{f}: PolicyException {name} waives hostPath into namespace {ns}, whose PSA enforce level is "
            f"{levels.get(ns, 'unknown (no Namespace manifest)')}; PSA forbids hostPath below privileged and "
            f"a Kyverno exception cannot waive it"
            for f, name, ns in hostpath_waivers(root) if levels.get(ns, "privileged") != "privileged"]


def test_every_hostpath_waiver_lands_in_a_privileged_namespace():
    assert list(hostpath_waivers()), "no hostPath waiver found: the k8s-infra exception moved or lost its policies"
    assert violations() == []


def test_a_waiver_into_a_restricted_namespace_is_refused(tmp_path):
    (tmp_path / "ns.yaml").write_text(yaml.safe_dump({"apiVersion": "v1", "kind": "Namespace", "metadata": {
        "name": "observability", "labels": {ENFORCE: "restricted"}}}))
    exc = yaml.safe_load((ROOT / "platform" / "edge" / "k8s-infra-exception.yaml").read_text())
    exc["spec"]["match"]["any"][0]["resources"]["namespaces"] = ["observability"]
    (tmp_path / "exc.yaml").write_text(yaml.safe_dump(exc))
    bad = violations(tmp_path)
    assert len(bad) == 1 and "restricted" in bad[0]

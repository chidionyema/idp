"""2026-08-31: tailscale/operator would not start for 2d15h and nothing in this repo could see it.

The pod said ``runAsNonRoot: true`` and named no ``runAsUser``. The image
(``ghcr.io/tailscale/k8s-operator:v1.102.3``) declares no USER, so it would run as uid 0 and the
kubelet refused it on every single attempt::

    Error: container has runAsNonRoot and image will run as root

That is a permanent refusal, not a transient one. Four Helm release revisions failed against it,
none was ever deployed, and ``helm rollback`` therefore answered "missing target release for
rollback: cannot remediate failed release" -- so the release could neither self-heal through
``upgrade.remediation.retries`` nor be cleared by hand. Kustomization/guacamole sat behind its
``dependsOn`` the whole time.

Nothing upstream of the kubelet could have caught it: the YAML is valid, ``helm template`` renders
it, and every posture policy in this estate reads ``runAsNonRoot: true`` and calls it correct. The
manifest looks MORE secure than one that names a uid. The contradiction only exists once the
image's config is merged with the pod's securityContext.

The control is a Kyverno ClusterPolicy on Pod (``nonroot-names-a-uid``), because admission is the
last point where all inputs merge and it covers pods no manifest declares -- the Tailscale
operator's own job is generating proxy StatefulSets from its config. This file is the CI half:
it grades the source this repo holds, so a PR is refused before the cluster ever has to.
"""

import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "platform" / "edge" / "require-runasuser-with-nonroot.yaml"


def _docs(path):
    try:
        return [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
    except yaml.YAMLError:
        return []


def _walk(node, trail=""):
    """Every mapping anywhere in a document, with the path that reached it.

    A recursive walk, not a pod-spec walk, and that is the point. The first version of this file
    walked ``spec.template.spec`` and passed green against the very manifest that caused the
    incident: in this estate a workload's securityContext usually lives inside a HelmRelease's
    ``values:`` block, which is not a pod spec and never will be. A check that cannot see where
    the setting actually lives is the silent-green class, so this one looks everywhere.
    """
    if isinstance(node, dict):
        yield trail, node
        for k, v in node.items():
            yield from _walk(v, f"{trail}.{k}" if trail else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, f"{trail}[{i}]")


def _offenders(root=None):
    """Documents that say non-root and never name a uid.

    Graded per document, not per mapping, because pod-level and container-level securityContexts
    are two halves of one answer: the kubelet takes the container's uid when it has one and the
    pod's otherwise, and in a Helm values block those two sit as siblings. A document that sets
    runAsNonRoot and names a uid *somewhere* has answered the question. A document that never
    names one has not -- it is trusting the image to declare a USER, which no reader of this repo
    can see and which any image bump can remove. That is the whole defect.
    """
    root = root or ROOT
    bad = []
    for path in sorted((root / "platform").rglob("*.yaml")):
        for doc in _docs(path):
            mappings = [m for _, m in _walk(doc)]
            says_nonroot = [m for m in mappings if m.get("runAsNonRoot") is True]
            if not says_nonroot:
                continue
            if any(m.get("runAsUser") for m in mappings):
                continue
            name = (doc.get("metadata") or {}).get("name", "?")
            bad.append(f"{path.relative_to(root)}::{doc.get('kind')}/{name}")
    return bad


def test_the_policy_file_is_wired_into_the_cluster_not_just_present():
    """A ClusterPolicy the kustomization does not name is a file, not a control (crew#488 CP5:
    kyverno-secrets-policy.yaml sat unreferenced since PR #259 and the cluster never held it)."""
    kust = yaml.safe_load(
        (ROOT / "platform" / "edge" / "kustomization.yaml").read_text()
    )
    assert "require-runasuser-with-nonroot.yaml" in kust["resources"]


def test_the_policy_enforces_rather_than_audits():
    """Audit would have bought nothing here and said something untrue. The Kyverno CLI counts an
    Audit violation in ``fail:`` exactly as it counts an Enforce one, so bin/idp-kyverno-render
    refuses the render either way -- an audited rule could not have landed any more easily than an
    enforcing one, it would only have read as weaker. The one chart in this estate carrying the
    same default (cert-manager v1.21.1) is fixed in the same commit, so Enforce refuses nothing
    that works today."""
    doc = next(d for d in _docs(POLICY) if d.get("kind") == "ClusterPolicy")
    rules = doc["spec"]["rules"]
    assert rules, "the policy declares no rules"
    for r in rules:
        assert r["validate"]["failureAction"] == "Enforce", (
            f"rule {r['name']} audits; an audited rule would have let this exact pod through"
        )


def test_the_policy_matches_pods_not_only_the_workloads_that_declare_them():
    """Operator-generated pods carry no Deployment in this repo. Matching Pod is the whole point."""
    doc = next(d for d in _docs(POLICY) if d.get("kind") == "ClusterPolicy")
    kinds = set()
    for r in doc["spec"]["rules"]:
        for m in r["match"]["any"]:
            kinds.update(m["resources"]["kinds"])
    assert "Pod" in kinds


def test_no_manifest_in_platform_says_nonroot_without_naming_a_uid():
    offenders = _offenders()
    assert not offenders, (
        "these pod specs would be refused by the kubelet on every attempt with 'container has "
        "runAsNonRoot and image will run as root' if their image declares no USER: "
        + ", ".join(offenders)
    )


@pytest.mark.parametrize(
    "psc,csc,expected_offender",
    [
        ({"runAsNonRoot": True}, {}, True),
        ({"runAsNonRoot": True, "runAsUser": 65532}, {}, False),
        ({"runAsNonRoot": True}, {"runAsUser": 65532}, False),
        ({}, {}, False),
    ],
)
def test_the_grader_itself_separates_the_two_shapes(
    tmp_path, psc, csc, expected_offender
):
    """The invariant above is only worth anything if the grader can tell the shapes apart -- a
    check that never fails is the silent-green class this estate keeps re-learning."""
    doc = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {"name": "probe"},
        "spec": {
            "securityContext": psc,
            "containers": [{"name": "c", "image": "x", "securityContext": csc}],
        },
    }
    plat = tmp_path / "platform"
    plat.mkdir()
    (plat / "probe.yaml").write_text(yaml.safe_dump(doc))
    assert bool(_offenders(root=tmp_path)) is expected_offender

"""2026-08-31 (crew#661 CP1): HelmRelease tailscale/tailscale-operator sat UpgradeFailed for 63
hours. Not the image name -- idp#1030 fixed that, and the registry-qualified image pulled clean
ten times in diagnose run 33354635731. The pod never started because the values patched
`runAsNonRoot: true` onto an image whose config declares no USER: the kubelet refused the
container 86 times in 28 minutes with "container has runAsNonRoot and image will run as root",
and the 102 re-pulls of a container that never ran then hit Docker Hub's unauthenticated pull
rate limit as a side effect. Forcing a uid instead is disproven upstream (tailscale/
tailscale#10638: the operator writes $HOME/.config at start and dies "permission denied" as
non-root), which also rules out readOnlyRootFilesystem -- the same write, refused one step later.

Class on the estate ledger: fix-proved-on-the-wrong-surface. The securityContext was proved
against the admission judge (kyverno render), never against the kubelet that runs the container;
the kubelet's runAsNonRoot check reads the image config, and no render ever does. These tests pin
the estate's answer: the two flags the image cannot satisfy are absent from the values, the
admission excuse covers BOTH rule spellings (original and autogen) on every surface that makes
the pod (the half-covered shape run 33335791923 already caught once), the excuse is wired into
the edge kustomization (the unreferenced-file class, crew#341), and everything the image CAN
satisfy still binds.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OPERATOR = ROOT / "platform" / "tailscale" / "operator.yaml"
EXCEPTION = ROOT / "platform" / "edge" / "tailscale-operator-exception.yaml"
EDGE_KUSTOMIZATION = ROOT / "platform" / "edge" / "kustomization.yaml"


def _operator_config():
    for doc in yaml.safe_load_all(OPERATOR.read_text()):
        if doc and doc.get("kind") == "HelmRelease":
            return doc["spec"]["values"]["operatorConfig"]
    raise AssertionError("no HelmRelease in platform/tailscale/operator.yaml")


def _root_image_exception():
    for doc in yaml.safe_load_all(EXCEPTION.read_text()):
        if (
            doc
            and doc.get("metadata", {}).get("name")
            == "tailscale-operator-image-runs-as-root"
        ):
            return doc
    raise AssertionError(
        "PolicyException tailscale-operator-image-runs-as-root is gone"
    )


def test_everything_the_image_can_satisfy_still_binds():
    """The exception must stay exactly as wide as what was measured, nothing wider."""
    oc = _operator_config()
    assert oc["podSecurityContext"]["seccompProfile"] == {"type": "RuntimeDefault"}
    sc = oc["securityContext"]
    assert sc["allowPrivilegeEscalation"] is False
    assert sc["capabilities"] == {"drop": ["ALL"]}
    assert sc["seccompProfile"] == {"type": "RuntimeDefault"}
    assert oc["resources"]["requests"] and oc["resources"]["limits"]


def test_the_exception_excuses_both_rule_spellings_on_every_pod_making_surface():
    """Kyverno judges the Deployment with the autogen rule and the Pod with the original; an
    exception naming only one spelling excused half the surfaces (run 33335791923)."""
    exc = _root_image_exception()
    assert exc["metadata"]["namespace"] == "kyverno", (
        "Kyverno honours exceptions from namespace kyverno only (crew#325)"
    )
    rules = {e["policyName"]: set(e["ruleNames"]) for e in exc["spec"]["exceptions"]}
    assert rules["require-run-as-nonroot"] == {
        "run-as-non-root",
        "autogen-run-as-non-root",
    }
    assert rules["require-ro-rootfs"] == {
        "validate-readOnlyRootFilesystem",
        "autogen-validate-readOnlyRootFilesystem",
    }
    (match,) = exc["spec"]["match"]["any"]
    res = match["resources"]
    assert set(res["kinds"]) == {"Deployment", "Pod", "ReplicaSet"}
    assert res["namespaces"] == ["tailscale"], "one namespace, nothing wider"
    assert res["names"] == ["operator*"], "one pod's names, nothing wider"


def test_the_exception_file_is_wired_into_the_edge_kustomization():
    """crew#341: a policy file no kustomization names never reaches the cluster."""
    kust = yaml.safe_load(EDGE_KUSTOMIZATION.read_text())
    assert "tailscale-operator-exception.yaml" in kust["resources"]

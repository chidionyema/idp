"""Road B raw operatorless calico-node must render and carry the estate's fixed parameters.

The live operator-based Calico is wedged (phantom underlay, calico-node CrashLoop). Road B
replaces it with a plain operatorless calico-node in the kubernetes datastore. The policy fences
#2111 merged are inert until such a datapath both reaches Ready AND advertises the real underlay;
a calico-node that autodetects a phantom interface (the .218 incident) enforces nothing across
nodes.

This test grades what a real render admission produces: it runs `kustomize build` over
`platform/calico/raw/` (the same tool `bin/idp-kubeconform` uses to grade policy on a Flux
Kustomization) and asserts the parsed structure of the RENDERED manifest -- a calico-node
DaemonSet that carries the kubernetes datastore, pins autodetection to enp0s6, and is VXLAN-only
-- not the source file's own text. Body of work is review-only: the raw dir is not yet wired to
un-suspend the `calico` Flux Kustomization (a separate cluster-control change).
"""

# ruff: noqa: S101

import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "platform" / "calico" / "raw"


def _rendered():
    """kustomize build the raw kustomization and return the parsed object list."""
    out = subprocess.run(
        ["kustomize", "build", str(RAW)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def _find(kind, name, docs):
    for d in docs:
        if d.get("kind") == kind and d.get("metadata", {}).get("name") == name:
            return d
    return None


render_available = pytest.mark.skipif(
    subprocess.run(["which", "kustomize"], capture_output=True).returncode != 0,
    reason="kustomize not on PATH",
)


@render_available
def test_render_produces_expected_kube_system_objects():
    """The kustomization renders the full operatorless deck into kube-system objects."""
    docs = _rendered()
    assert _find("ConfigMap", "calico-config", docs), "calico-config ConfigMap"
    assert _find("DaemonSet", "calico-node", docs), "calico-node DaemonSet"
    assert _find("Deployment", "calico-kube-controllers", docs), (
        "missing kube-controllers"
    )
    # ServiceAccounts / ClusterRoles / Bindings for node, cni-plugin, controllers.
    for sa in ("calico-node", "calico-cni-plugin", "calico-kube-controllers"):
        assert _find("ServiceAccount", sa, docs), f"missing ServiceAccount {sa}"
    # The cluster-scoped RBAC carries the estate prefix, and this is load-bearing rather than
    # cosmetic: a ClusterRole has no namespace, so moving the ServiceAccounts into kube-system did
    # not separate this deck's roles from the removed tigera-operator's. The operator left
    # ClusterRole/calico-node and ClusterRole/calico-cni-plugin stuck in Terminating on a
    # tigera.io/cni-protector finalizer no surviving controller can clear, and while this deck
    # claimed those same names the Kustomization waited on tombstones -- so it never completed,
    # and therefore never pruned the superseded operator HelmRelease it was meant to remove.
    for name in ("calico-node", "calico-cni-plugin", "calico-kube-controllers"):
        assert not _find("ClusterRole", name, docs), (
            f"ClusterRole/{name} is a name the tigera-operator also owns"
        )
        role = _find("ClusterRole", f"estate-{name}", docs)
        binding = _find("ClusterRoleBinding", f"estate-{name}", docs)
        assert role and binding, f"missing estate-{name} ClusterRole/Binding"
        # The binding points at the prefixed role, and still at the unprefixed ServiceAccount:
        # ServiceAccounts are namespaced in kube-system and never collided in the first place.
        assert binding["roleRef"]["name"] == f"estate-{name}"
        assert [
            (s["kind"], s["name"], s.get("namespace")) for s in binding["subjects"]
        ] == [("ServiceAccount", name, "kube-system")]


@render_available
def test_rendered_node_uses_kubernetes_datastore_in_kube_system():
    """The rendered calico-node is operatorless (kubernetes datastore), not calico-system."""
    ds = _find("DaemonSet", "calico-node", _rendered())
    assert ds["metadata"]["namespace"] == "kube-system"
    env = {
        e["name"]: e.get("value")
        for c in ds["spec"]["template"]["spec"]["containers"]
        for e in c.get("env", [])
    }
    assert env.get("DATASTORE_TYPE") == "kubernetes"


@render_available
def test_rendered_node_pins_autodetection_to_enp0s6():
    """IP_AUTODETECTION_METHOD must pin enp0s6 -- the exact phantom-underlay fix."""
    ds = _find("DaemonSet", "calico-node", _rendered())
    env = {
        e["name"]: e.get("value")
        for c in ds["spec"]["template"]["spec"]["containers"]
        for e in c.get("env", [])
    }
    assert env.get("IP_AUTODETECTION_METHOD") == "interface=enp0s6", (
        "phantom-underlay fix required"
    )


@render_available
def test_rendered_node_is_vxlan_not_ipip_over_flannel_cidr():
    """Rendered node keeps flannel's 10.244.0.0/16 CIDR and runs VXLAN, not IPIP.

    CALICO_NETWORKING_BACKEND has no literal "vxlan" value in Calico OSS (valid: bird / none);
    VXLAN is driven by FELIX_VXLANENABLED + the pool's VXLAN/encapsulation knobs.
    """
    ds = _find("DaemonSet", "calico-node", _rendered())
    env = {
        e["name"]: e.get("value")
        for c in ds["spec"]["template"]["spec"]["containers"]
        for e in c.get("env", [])
    }
    assert env.get("CALICO_IPV4POOL_CIDR") == "10.244.0.0/16"
    assert env.get("CALICO_IPV4POOL_IPIP") in ("None", "Never")
    assert env.get("CALICO_IPV4POOL_VXLAN") in ("Always", "CrossSubnet")
    assert env.get("FELIX_VXLANENABLED") == "true"
    assert env.get("CALICO_NETWORKING_BACKEND") in ("bird", "none", None)


@render_available
def test_rendered_node_pins_v322_with_install_cni():
    """Rendered DaemonSet uses v3.32.2 images and an install-cni init writing /etc/cni/net.d."""
    ds = _find("DaemonSet", "calico-node", _rendered())
    spec = ds["spec"]["template"]["spec"]
    images = [c["image"] for c in spec["containers"]]
    inits = [c["image"] for c in spec.get("initContainers", [])]
    assert any("calico/node:v3.32.2" in i for i in images), images
    assert any("calico/cni:v3.32.2" in i for i in inits), inits
    installer = next(
        (c for c in spec.get("initContainers", []) if c["name"] == "install-cni"), None
    )
    assert installer and any(
        m["mountPath"] == "/host/etc/cni/net.d" for m in installer["volumeMounts"]
    )


@render_available
def test_rendered_config_disables_typha():
    """The operator path's typha bloat is off in the operatorless config."""
    cm = _find("ConfigMap", "calico-config", _rendered())
    assert cm["data"]["typha_service_name"] == "none"

"""crew#412 row 2 (R38): the founder's Kubernetes view is the Backstage portal, not a second
dashboard. On 2026-08-27 the founder's pasted plan was `kubectl apply` of the upstream
Kubernetes Dashboard with a cluster-admin token behind `kubectl proxy` on the laptop. This
test holds the rule that replaced it: the catalogue pod reads the cluster it runs in, with a
role that can only read, and the founder entities say which workloads they show.

Incident test (rung 4). Three assertions on the rendered OKE overlay and the config, and
the refuse case: a write verb on the role fails."""
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "platform" / "backstage" / "overlays" / "oke"
WRITE_VERBS = {"create", "update", "patch", "delete", "deletecollection", "*"}


def _rendered():
    out = subprocess.run(
        ["kubectl", "kustomize", "--load-restrictor", "LoadRestrictionsNone", str(OVERLAY)],
        capture_output=True, text=True, check=True).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def _by_kind(docs, kind):
    return [d for d in docs if d.get("kind") == kind]


def test_catalogue_pod_reads_the_cluster_with_its_own_read_only_role():
    docs = _rendered()
    dep = next(d for d in _by_kind(docs, "Deployment") if d["metadata"]["name"] == "catalogue")
    spec = dep["spec"]["template"]["spec"]
    assert spec["serviceAccountName"] == "catalogue"
    assert spec.get("automountServiceAccountToken") is True
    (role,) = _by_kind(docs, "ClusterRole")
    verbs = {v for r in role["rules"] for v in r["verbs"]}
    assert verbs and not verbs & WRITE_VERBS, f"write verb on the portal's role: {verbs & WRITE_VERBS}"
    (binding,) = _by_kind(docs, "ClusterRoleBinding")
    assert binding["roleRef"]["name"] == role["metadata"]["name"]
    assert binding["subjects"] == [{"kind": "ServiceAccount", "name": "catalogue", "namespace": "backstage"}]


def test_a_write_verb_on_the_role_is_refused():
    docs = _rendered()
    (role,) = _by_kind(docs, "ClusterRole")
    role["rules"][0]["verbs"].append("delete")
    verbs = {v for r in role["rules"] for v in r["verbs"]}
    assert verbs & WRITE_VERBS == {"delete"}


def test_plugin_reads_in_cluster_with_the_pod_token_and_the_founder_entities_select_workloads():
    cfg = yaml.safe_load((ROOT / "backstage" / "app-config.container.yaml").read_text())
    (cluster,) = cfg["kubernetes"]["clusterLocatorMethods"][0]["clusters"]
    assert cluster["url"] == "https://kubernetes.default.svc"
    assert cluster["authProvider"] == "serviceAccount"
    assert cluster["skipTLSVerify"] is False
    assert "serviceAccountToken" not in cluster, "a pasted token is a secret in git; the pod's mount is the token"
    dev = yaml.safe_load((ROOT / "backstage" / "app-config.yaml").read_text())
    assert not (dev.get("kubernetes") or {}), "the compose run has no cluster; the block lives in the container config"
    ents = {e["metadata"]["name"]: e for e in yaml.safe_load_all((ROOT / "backstage" / "founder" / "catalog-info.yaml").read_text()) if e}
    sel = "backstage.io/kubernetes-label-selector"
    assert ents["founder-catalogue"]["metadata"]["annotations"][sel] == "app.kubernetes.io/part-of=idp"
    assert ents["founder-model-router"]["metadata"]["annotations"][sel] == "app.kubernetes.io/name=litellm"

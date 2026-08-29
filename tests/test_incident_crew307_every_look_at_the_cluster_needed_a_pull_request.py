"""crew#307, 2026-08-29. The founder's surfaces vanished from the portal and nobody could read the
catalogue pod without merging a pull request into the break-glass playbook: the laptop key was
retired (crew#227) and no other door existed. Founder: "we need to be able to debug the cluster",
"from the Mac also", "the point is we should be portable". The door is the Tailscale operator's
API-server proxy: tailnet identity in, Kubernetes group out, bound by RBAC. This pins the three
pieces so none can be switched off alone."""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TS = ROOT / "platform" / "tailscale"


def _hujson(path):
    text = re.sub(r"//[^\n]*", "", path.read_text())
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return json.loads(text)


def test_the_operator_fronts_the_api_server_on_the_tailnet():
    docs = list(yaml.safe_load_all((TS / "operator.yaml").read_text()))
    hr = next(d for d in docs if d and d["kind"] == "HelmRelease")
    assert hr["spec"]["values"]["apiServerProxyConfig"]["mode"] == "auth"


def test_the_founder_group_is_granted_a_kubernetes_group():
    pol = _hujson(TS / "policy.hujson")
    assert "tag:k8s-operator" in pol["tagOwners"]
    grant = next(g for g in pol["grants"] if "tag:k8s-operator" in g["dst"])
    assert "group:founder" in grant["src"]
    caps = grant["app"]["tailscale.com/cap/kubernetes"]
    assert caps[0]["impersonate"]["groups"] == ["estate:founder"]
    assert any("tag:k8s-operator:443" in a["dst"] and "group:founder" in a["src"] for a in pol["acls"])


def test_the_kubernetes_group_is_bound_and_wired():
    crb = yaml.safe_load((TS / "rbac.yaml").read_text())
    assert crb["kind"] == "ClusterRoleBinding"
    assert crb["roleRef"]["name"] == "cluster-admin"
    assert crb["subjects"] == [{"apiGroup": "rbac.authorization.k8s.io", "kind": "Group", "name": "estate:founder"}]
    kust = yaml.safe_load((TS / "kustomization.yaml").read_text())
    assert "rbac.yaml" in kust["resources"]

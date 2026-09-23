"""crew#718: the cluster doctor's findings reach the founder, on the Ops page.

The class of mistake (founder, 2026-09-01: "we did not conclude the cluster gpt, i need to be
using it ... no black boxes in estate ... everything must be visible to founder"): K8sGPT
(platform/healing) had analysed the cluster since 2026-08-27 and written every diagnosis to a
Result object that no page listed and no person opened; a Prometheus rule counted them and
called that "read" (LAW 28, the instrument-nobody-reads class). This test pins the four
pieces that make a finding visible, so none can be dropped alone:

1. the portal's cluster role may list Result objects, and only read them (crew#412 stays);
2. the Kubernetes plugin knows the Result kind, so the entity tab lists it;
3. the Ops page reads the doctor's own Deployment by the name the manifest gives the K8sGPT
   object, so "no findings" is never confused with "no doctor";
4. the login drill grades the tile's words on /ops, so a broken read fails the hourly drill.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RBAC = ROOT / "platform/backstage/base/rbac.yaml"
APP_CONFIG = ROOT / "backstage/app-config.container.yaml"
K8SGPT = ROOT / "platform/healing/analyzer/k8sgpt.yaml"
FINDINGS = ROOT / "backstage/packages/app/src/modules/home/findings.ts"
OPS = ROOT / "backstage/packages/app/src/modules/home/Ops.tsx"
CATALOG = ROOT / "backstage/founder/catalog-info.yaml"
DRILL = ROOT / "bin/idp-login-drill"


def _docs(path: Path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_the_portal_may_list_the_doctors_results_and_only_read_them():
    role = next(d for d in _docs(RBAC) if d["kind"] == "ClusterRole")
    rows = [r for r in role["rules"] if "core.k8sgpt.ai" in r.get("apiGroups", [])]
    assert rows, (
        "the cluster role never grants core.k8sgpt.ai, so the Ops page answers 403"
    )
    assert rows[0]["resources"] == ["results"]
    assert set(rows[0]["verbs"]) <= {"get", "list", "watch"}


def test_the_kubernetes_plugin_knows_the_result_kind():
    cfg = yaml.safe_load(APP_CONFIG.read_text())
    crs = cfg["kubernetes"].get("customResources", [])
    assert {
        "group": "core.k8sgpt.ai",
        "apiVersion": "v1alpha1",
        "plural": "results",
    } in crs


def test_the_ops_page_names_the_doctor_as_the_manifest_does():
    doctor = next(d for d in _docs(K8SGPT) if d["kind"] == "K8sGPT")
    src = FINDINGS.read_text()
    assert f"DOCTOR_NAMESPACE = '{doctor['metadata']['namespace']}'" in src
    assert f"DOCTOR_NAME = '{doctor['metadata']['name']}'" in src


def test_the_ops_page_shows_the_diagnosis_and_says_when_the_doctor_is_down():
    src = OPS.read_text()
    assert 'data-testid="ops-doctor"' in src
    assert "f.details" in src, (
        "the tile drops the model's diagnosis, the one thing to read"
    )
    assert "The cluster doctor could not be read" in src


def test_the_healing_entity_lists_the_results_on_its_kubernetes_tab():
    entity = next(
        d
        for d in _docs(CATALOG)
        if d.get("metadata", {}).get("name") == "founder-healing"
    )
    ann = entity["metadata"]["annotations"]
    doctor = next(d for d in _docs(K8SGPT) if d["kind"] == "K8sGPT")
    assert ann["backstage.io/kubernetes-namespace"] == doctor["metadata"]["namespace"]
    assert ann["backstage.io/kubernetes-label-selector"] == (
        f"k8sgpts.k8sgpt.ai/name={doctor['metadata']['name']}"
    )
    assert "no-screen" not in entity["metadata"].get("tags", [])


def test_the_login_drill_grades_the_doctor_tile_on_ops():
    table = re.search(r"PUBLISHED = \((.*?)\n    \)", DRILL.read_text(), re.S).group(1)
    assert '("ops", "text=Cluster doctor")' in table

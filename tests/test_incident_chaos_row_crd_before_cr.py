"""Incident 2026-08-25: the `chaos` Flux row carried the Chaos Mesh HelmRelease and a
chaos-mesh.org Schedule in one Kustomization. Flux server-side dry-runs the whole row, the
Schedule CRD did not exist yet, the row failed every reconcile and Chaos Mesh was never
installed (24 h, flux events: no matches for kind "Schedule" in version chaos-mesh.org/v1alpha1).
Rule (rung 4): a Flux Kustomization path that installs a HelmRelease carries no resource whose
API group is outside the groups the cluster has before that chart lands."""
import glob
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Groups present before any HelmRelease in the estate applies: core, k8s built-ins, Flux, and
# the groups installed by rows that every HelmRelease row is ordered after (CRDs rows).
PRE_INSTALLED = {
    "",
    "apps",
    "batch",
    "rbac.authorization.k8s.io",
    "networking.k8s.io",
    "policy",
    "storage.k8s.io",
    "apiextensions.k8s.io",
    "scheduling.k8s.io",
    "autoscaling",
    "source.toolkit.fluxcd.io",
    "helm.toolkit.fluxcd.io",
    "kustomize.toolkit.fluxcd.io",
    "notification.toolkit.fluxcd.io",
    "gateway.networking.k8s.io",
    "external-secrets.io",
    "cert-manager.io",
    "kyverno.io",
    "traefik.io",
}


def _group(api_version):
    return api_version.split("/")[0] if "/" in api_version else ""


def _paths():
    for f in sorted(glob.glob(str(ROOT / "clusters" / "*" / "*.yaml"))):
        for d in yaml.safe_load_all(open(f)):
            if d and d.get("kind") == "Kustomization" and d["spec"].get("path"):
                yield d["metadata"]["name"], ROOT / d["spec"]["path"]


def _docs(path):
    out = subprocess.run(["kubectl", "kustomize", "--load-restrictor", "LoadRestrictionsNone", str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    return [d for d in yaml.safe_load_all(out.stdout) if d]


def _offenders(docs):
    if not any(d.get("kind") == "HelmRelease" for d in docs):
        return []
    return sorted(f"{d['kind']}/{d['metadata']['name']}" for d in docs
                  if _group(d["apiVersion"]) not in PRE_INSTALLED)


def test_no_flux_row_installs_a_chart_and_its_own_custom_resources():
    seen = 0
    for name, path in _paths():
        docs = _docs(path)
        if docs is None:
            continue   # rows needing gitignored inputs render elsewhere (test_incident_backstage_*)
        seen += 1
        assert _offenders(docs) == [], f"row {name} ({path}): CRs dry-run before their CRD exists"
    assert seen > 0


def test_the_incident_shape_is_refused():
    docs = [{"apiVersion": "helm.toolkit.fluxcd.io/v2", "kind": "HelmRelease", "metadata": {"name": "chaos-mesh"}},
            {"apiVersion": "chaos-mesh.org/v1alpha1", "kind": "Schedule", "metadata": {"name": "backstage-pod-kill"}}]
    assert _offenders(docs) == ["Schedule/backstage-pod-kill"]
    assert _offenders(docs[:1]) == [] and _offenders(docs[1:]) == []

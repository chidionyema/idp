"""crew#503, 2026-08-27 15:05Z: a configMapGenerator in backstage/founder/kustomization.yaml rendered
`ConfigMap/founder-catalog` with no namespace. Flux refused the whole backstage Kustomization
("ConfigMap/founder-catalog namespace not specified: the server could not find the requested resource")
and the seven Kustomizations that depend on it (observability, spire, temporal, image-automation,
chaos-mesh, chaos, cluster-state) went not-Ready with it. `kustomize build` had passed: it does not
check namespaces, the API server does.

Guard (LAW 45): every overlay a Flux Kustomization in clusters/*/ points at is rendered here and every
namespaced object in it must carry metadata.namespace. Runs kustomize only; no socket.
"""
import glob
import os
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLUSTER_SCOPED = {
    "Namespace", "CustomResourceDefinition", "StorageClass", "PriorityClass", "IngressClass", "RuntimeClass",
    "GatewayClass", "Node", "PersistentVolume", "CSIDriver", "APIService", "MutatingWebhookConfiguration",
    "ValidatingWebhookConfiguration", "ValidatingAdmissionPolicy", "ValidatingAdmissionPolicyBinding",
}


def flux_paths():
    out = set()
    for f in glob.glob(str(ROOT / "clusters" / "*" / "*.yaml")):
        for d in yaml.safe_load_all(open(f)):
            if isinstance(d, dict) and d.get("kind") == "Kustomization" and d.get("spec", {}).get("path"):
                p = ROOT / d["spec"]["path"].lstrip("./")
                if (p / "kustomization.yaml").is_file():
                    out.add(str(p.relative_to(ROOT)))
    return sorted(out)


def render(path):
    r = subprocess.run(["kustomize", "build", str(ROOT / path)], capture_output=True, text=True)
    assert r.returncode == 0, f"kustomize build {path}: {r.stderr[-800:]}"
    return [d for d in yaml.safe_load_all(r.stdout) if isinstance(d, dict) and "kind" in d]


@pytest.mark.skipif(shutil.which("kustomize") is None, reason="kustomize not on PATH")
@pytest.mark.parametrize("path", flux_paths())
def test_incident_crew503_every_namespaced_object_in_a_flux_path_names_its_namespace(path):
    missing = []
    for d in render(path):
        kind = d["kind"]
        if kind in CLUSTER_SCOPED or kind.startswith("Cluster"):
            continue
        if not d.get("metadata", {}).get("namespace"):
            missing.append(f"{kind}/{d['metadata'].get('name')}")
    assert not missing, f"{path}: Flux will refuse the whole Kustomization for {missing}"


def test_incident_crew503_the_founder_catalog_configmap_is_in_the_backstage_namespace():
    cms = [d for d in render("platform/backstage/overlays/oke")
           if d["kind"] == "ConfigMap" and d["metadata"]["name"] == "founder-catalog"]
    assert cms and cms[0]["metadata"].get("namespace") == "backstage", cms

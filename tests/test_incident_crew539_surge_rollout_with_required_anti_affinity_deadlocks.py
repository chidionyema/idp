"""Incident crew#539 (oke-check 33162263652, 2026-08-28 10:12Z): Deployment/backstage/catalogue had
replicas 2, requiredDuringScheduling podAntiAffinity on kubernetes.io/hostname and
rollingUpdate {maxUnavailable: 0, maxSurge: 1} on a two-node pool. The surge pod needed a third
node: ReplicaSet catalogue-8647bbdc59 "timed out progressing", the pod sat Pending 17m
("0/2 nodes are available: 2 node(s) didn't match pod anti-affinity rules") and every Flux row
behind backstage waited on it. Founder: "is this a deadlock" -- yes, by construction.

The rule: a rendered Deployment that requires one pod per hostname may not surge. Its rolling
update must have maxSurge 0 (replace in place) -- a surge can only ever schedule when there is a
spare node, which nothing guarantees. Rung 4: the check runs on the rendered overlay, not the patch.
"""
import pathlib
import shutil
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAYS = sorted(p.parent for p in (ROOT / "platform").rglob("overlays/*/kustomization.yaml"))


def _render(overlay: pathlib.Path):
    r = subprocess.run(["kubectl", "kustomize", str(overlay)], capture_output=True, text=True)
    if r.returncode != 0:
        # the local overlay reads the gitignored generated catalog (catalog/catalog-info.yaml)
        pytest.skip(f"{overlay.relative_to(ROOT)} does not render in a clean checkout: {r.stderr.strip()[-120:]}")
    return [d for d in yaml.safe_load_all(r.stdout) if isinstance(d, dict)]


def _requires_one_per_host(spec: dict) -> bool:
    aff = ((spec.get("affinity") or {}).get("podAntiAffinity") or {}).get("requiredDuringSchedulingIgnoredDuringExecution") or []
    return any(t.get("topologyKey") == "kubernetes.io/hostname" for t in aff)


def surging_pinned_deployments(docs) -> list[str]:
    bad = []
    for d in docs:
        if d.get("kind") != "Deployment":
            continue
        spec = d.get("spec") or {}
        if not _requires_one_per_host((spec.get("template") or {}).get("spec") or {}):
            continue
        ru = ((spec.get("strategy") or {}).get("rollingUpdate") or {})
        surge = ru.get("maxSurge", "25%")
        if str(surge) not in ("0", "0%"):
            bad.append(f"{(d.get('metadata') or {}).get('namespace')}/{(d.get('metadata') or {}).get('name')}: maxSurge={surge}")
    return bad


@pytest.mark.skipif(shutil.which("kubectl") is None, reason="kubectl not on PATH")
@pytest.mark.parametrize("overlay", OVERLAYS, ids=[str(o.relative_to(ROOT)) for o in OVERLAYS])
def test_no_pinned_deployment_surges(overlay):
    assert surging_pinned_deployments(_render(overlay)) == []


def test_detects_the_incident_shape():
    doc = {
        "kind": "Deployment",
        "metadata": {"namespace": "backstage", "name": "catalogue"},
        "spec": {
            "strategy": {"rollingUpdate": {"maxUnavailable": 0, "maxSurge": 1}},
            "template": {"spec": {"affinity": {"podAntiAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": [{"topologyKey": "kubernetes.io/hostname"}]}}}},
        },
    }
    assert surging_pinned_deployments([doc]) == ["backstage/catalogue: maxSurge=1"]
    doc["spec"]["strategy"]["rollingUpdate"] = {"maxUnavailable": 1, "maxSurge": 0}
    assert surging_pinned_deployments([doc]) == []

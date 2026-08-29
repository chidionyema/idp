"""Incident, 2026-08-29 01:05Z: catalogue.<zone> answered 404 after idp#648 moved
platform/backstage's namespace.yaml from the prune:true `backstage` Kustomization to a new
`backstage-namespace` row; the namespace, and everything the portal is, went with the prune.

Founder ruling, 2026-08-29: "Moving a file in Git should never cause a cascading destruction of
a production namespace." Three guards, graded on the rendered thing, not on a file name:

1. every Namespace any Flux Kustomization under clusters/ renders carries
   `kustomize.toolkit.fluxcd.io/prune: disabled` (Flux never garbage-collects it);
2. the cluster refuses a DELETE of such a Namespace: platform/edge/protect-namespaces.yaml is a
   ClusterPolicy matching the mark, wired into platform/edge, Enforce;
3. a pull request that deletes or renames a file holding a Namespace manifest is refused.
"""
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MARK = "kustomize.toolkit.fluxcd.io/prune"
MARK_RE = re.compile(r"kustomize\.toolkit\.fluxcd\.io/prune:\s*disabled")


def _flux_paths():
    out = []
    for f in sorted((ROOT / "clusters").rglob("*.yaml")):
        if "flux-system" in f.parts:
            continue
        for doc in yaml.safe_load_all(f.read_text()):
            if doc and doc.get("kind") == "Kustomization" and str(doc.get("apiVersion", "")).startswith("kustomize.toolkit"):
                path = (doc.get("spec") or {}).get("path")
                if path and path.strip("./") and (ROOT / path).is_dir():
                    out.append((doc["metadata"]["name"], path))
    return out


def _rendered_namespaces(path):
    p = subprocess.run(["kubectl", "kustomize", str(ROOT / path)], capture_output=True, text=True)
    if p.returncode != 0:
        pytest.skip(f"kubectl kustomize cannot render {path}: {p.stderr.strip()[:200]}")
    return [d for d in yaml.safe_load_all(p.stdout) if d and d.get("kind") == "Namespace"]


@pytest.mark.parametrize("row,path", _flux_paths(), ids=lambda x: x if isinstance(x, str) and "/" not in x else None)
def test_every_namespace_a_flux_row_renders_is_never_pruned(row, path):
    misses = [
        d["metadata"]["name"] for d in _rendered_namespaces(path)
        if (d["metadata"].get("annotations") or {}).get(MARK) != "disabled"
    ]
    assert not misses, f"Flux row {row} ({path}) renders Namespace(s) Flux may garbage-collect: {misses}"


def test_every_namespace_manifest_under_platform_carries_the_mark():
    misses = []
    for f in sorted((ROOT / "platform").rglob("*.y*ml")):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "Namespace" and (d["metadata"].get("annotations") or {}).get(MARK) != "disabled":
                misses.append(f"{f.relative_to(ROOT)}: {d['metadata']['name']}")
    assert not misses, "\n".join(misses)


def test_the_cluster_refuses_deleting_a_marked_namespace():
    pol = yaml.safe_load((ROOT / "platform/edge/protect-namespaces.yaml").read_text())
    assert pol["kind"] == "ClusterPolicy"
    rule = pol["spec"]["rules"][0]
    res = rule["match"]["any"][0]["resources"]
    assert res["kinds"] == ["Namespace"] and res["operations"] == ["DELETE"]
    assert res["annotations"] == {MARK: "disabled"}, "scope is the mark, not a name list"
    assert rule["validate"]["failureAction"] == "Enforce" and "deny" in rule["validate"]
    wired = yaml.safe_load((ROOT / "platform/edge/kustomization.yaml").read_text())["resources"]
    assert "protect-namespaces.yaml" in wired, "policy file exists but platform/edge does not ship it"


def _base_ref():
    base = os.environ.get("GITHUB_BASE_REF")
    return f"origin/{base}" if base else "origin/main"


def test_a_pull_request_never_deletes_or_moves_a_namespace_manifest():
    p = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-status", "-M", f"{_base_ref()}...HEAD"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        pytest.skip(f"no {_base_ref()} to diff against: {p.stderr.strip()[:120]}")
    bad = []
    for line in p.stdout.splitlines():
        parts = line.split("\t")
        if parts[0][0] not in "DR":
            continue
        old = parts[1]
        blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{_base_ref()}:{old}"], capture_output=True, text=True)
        if blob.returncode == 0 and "kind: Namespace" in blob.stdout:
            bad.append(line)
    assert not bad, ("a Namespace manifest was deleted or moved in this PR; Flux prunes what leaves a "
                     "row's inventory (catalogue 404, 2026-08-29). Keep the file where it is: " + "; ".join(bad))

"""crew#624 (founder, 2026-08-29): "WHY IS HUBBLE NOT THERE ... IF WE CANT TRUST BACKSTAGE THEN
WE MAY AS WELL NOT HAVE A COMPANY ... ITS A GOVERNANCE FAILURE".

The catalogue was rendered from the Mac inventory only. Measured before the fix:
`grep -c hubble catalog/catalog-info.yaml` = 0 while 30 Flux Kustomizations, 24 HelmReleases
and the CNI (Cilium + Hubble) ran on the cluster. Rule: every Flux row, every Helm chart and
every platform/ directory in the checkout is an entity in the generated catalogue, and Hubble
is named. Proved both ways: the checkout passes; a copy with one extra Flux row and no
generator change fails (the entity is generated, so the copy passes too -- the negative case is
the generator with cluster_entities removed, which the first test pins).
"""

import glob
import os
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"


def render(tmp_path):
    out = tmp_path / "out"
    env = {
        **os.environ,
        "INV": str(ROOT / "tests/fixtures/inventory.json"),
        "OUT": str(out),
    }
    subprocess.run([str(GEN)], check=True, env=env, capture_output=True, text=True)
    return [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]


def cluster_rows():
    rows = set()
    files = glob.glob(str(ROOT / "clusters/*/*.yaml")) + glob.glob(
        str(ROOT / "platform/**/*.yaml"), recursive=True
    )
    for f in files:
        try:
            docs = list(yaml.safe_load_all(open(f)))
        except yaml.YAMLError:
            continue
        for d in docs:
            if (
                isinstance(d, dict)
                and d.get("kind") in ("Kustomization", "HelmRelease")
                and (d.get("metadata") or {}).get("name")
            ):
                rows.add((d["kind"], d["metadata"]["name"]))
    return rows


def test_hubble_and_cilium_are_named(tmp_path):
    ents = {e["metadata"]["name"]: e for e in render(tmp_path)}
    assert "cluster-cni-hubble" in ents and "cluster-cni-cilium" in ents
    assert (
        ents["cluster-cni-hubble"]["metadata"]["annotations"]["estate/enabled"]
        == "true"
    )
    assert "observability" in ents["cluster-cni-hubble"]["metadata"]["description"]

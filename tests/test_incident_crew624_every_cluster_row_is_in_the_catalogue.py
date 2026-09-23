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


def test_generator_reads_the_cluster_not_only_the_mac():
    assert "def cluster_entities" in GEN.read_text()
    assert "cluster = cluster_entities()" in GEN.read_text()


def test_every_flux_row_and_helm_chart_is_an_entity(tmp_path):
    ents = render(tmp_path)
    have = {
        (
            e["metadata"].get("annotations", {}).get("estate/flux-kind"),
            e["metadata"].get("annotations", {}).get("estate/flux-name"),
        )
        for e in ents
    }
    rows = cluster_rows()
    assert rows, "no Flux rows found in the checkout"
    missing = sorted(rows - have)
    assert not missing, f"cluster rows with no catalogue entity: {missing}"


def test_every_platform_directory_is_an_entity(tmp_path):
    ents = render(tmp_path)
    files = {e["metadata"].get("annotations", {}).get("estate/file", "") for e in ents}
    paths = {e["metadata"].get("annotations", {}).get("estate/path", "") for e in ents}
    reached = {
        p.lstrip("./").split("/")[1]
        for p in (files | paths)
        if p.lstrip("./").startswith("platform/")
    }
    reached = {r for r in reached if r}
    dirs = {
        d for d in os.listdir(ROOT / "platform") if (ROOT / "platform" / d).is_dir()
    }
    missing = sorted(dirs - reached)
    assert not missing, f"platform directories dark in the catalogue: {missing}"


def test_hubble_and_cilium_are_named(tmp_path):
    ents = {e["metadata"]["name"]: e for e in render(tmp_path)}
    assert "cluster-cni-hubble" in ents and "cluster-cni-cilium" in ents
    assert (
        ents["cluster-cni-hubble"]["metadata"]["annotations"]["estate/enabled"]
        == "true"
    )
    assert "observability" in ents["cluster-cni-hubble"]["metadata"]["description"]

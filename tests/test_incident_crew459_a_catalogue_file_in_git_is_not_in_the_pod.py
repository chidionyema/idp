"""crew#459, 2026-08-31. A catalogue file added to git and registered in
backstage/app-config.yaml changes nothing the founder or a buyer can see: the deployed pod
reads app-config.container.yaml, whose locations are all /estate/* paths fed by ConfigMaps
that the oke overlay projects. backstage/org/catalog-info.yaml was written and registered in
the developer config alone, so every ownedBy relation would still have pointed at a Group
that does not exist in the cluster -- the estate's third-commonest mistake class,
fix-proved-on-the-wrong-surface. This pins the whole road for each hand-written catalogue
directory: a kustomization that generates the ConfigMap, the overlay that projects it at the
path the config names, and a location in the container config that allows the kinds the file
actually holds.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTAINER = ROOT / "backstage" / "app-config.container.yaml"
OVERLAY = ROOT / "platform" / "backstage" / "overlays" / "oke" / "kustomization.yaml"

# directory in backstage/ -> the ConfigMap its kustomization generates
CATALOGUE_DIRS = {
    "org": "org-catalog",
    "founder": "founder-catalog",
    "platform": "platform-catalog",
}


def _container_locations():
    doc = yaml.safe_load(CONTAINER.read_text())
    return doc["catalog"]["locations"]


def test_every_catalogue_directory_generates_a_namespaced_configmap():
    for directory, configmap in CATALOGUE_DIRS.items():
        kust = ROOT / "backstage" / directory / "kustomization.yaml"
        assert kust.is_file(), (
            f"backstage/{directory} has no kustomization.yaml; Flux cannot ship it"
        )
        doc = yaml.safe_load(kust.read_text())
        gen = doc["configMapGenerator"][0]
        assert gen["name"] == configmap
        # crew#503, 2026-08-27 15:05Z: a generated ConfigMap with no namespace fails the
        # backstage Flux Kustomization and takes its dependents with it.
        assert gen["namespace"] == "backstage", f"{configmap} has no namespace"
        assert "catalog-info.yaml" in gen["files"]


def test_the_org_groups_exist_and_are_the_owner_every_generator_stamps():
    """bin/catalog-gen stamps one owner on every entity it emits. That Group has to be here."""
    gen = (ROOT / "bin" / "catalog-gen").read_text()
    owner = re.search(r'^OWNER\s*=\s*"([^"]+)"', gen, re.M).group(1)
    assert owner.startswith("group:default/"), owner
    groups = {
        d["metadata"]["name"]
        for d in yaml.safe_load_all(
            (ROOT / "backstage" / "org" / "catalog-info.yaml").read_text()
        )
        if d and d["kind"] == "Group"
    }
    assert owner.split("/")[-1] in groups, (
        f"bin/catalog-gen stamps owner {owner} on every entity and no Group by that name exists"
    )

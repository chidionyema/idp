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


def test_the_overlay_projects_every_catalogue_configmap_at_the_path_the_config_names():
    overlay = OVERLAY.read_text()
    targets = {loc["target"] for loc in _container_locations() if loc["type"] == "file"}
    for directory, configmap in CATALOGUE_DIRS.items():
        assert f"../../../../backstage/{directory}\n" in overlay, (
            f"backstage/{directory} is not a resource of the oke overlay, so {configmap} is never rendered"
        )
        if (
            configmap == "founder-catalog"
            or configmap == "platform-catalog"
            or configmap == "org-catalog"
        ):
            assert re.search(rf"name: {configmap}\b", overlay), (
                f"{configmap} is not projected"
            )
        # the estate ConfigMap fills /estate itself; the rest land in a subdirectory of it
        assert f"/estate/{directory}/catalog-info.yaml" in targets, (
            f"app-config.container.yaml names no location at /estate/{directory}/catalog-info.yaml"
        )
        assert f"path: {directory}/catalog-info.yaml" in overlay, (
            f"the overlay does not project {configmap} at {directory}/catalog-info.yaml"
        )


def test_the_container_config_allows_the_kinds_each_file_actually_holds():
    """A kind missing from a location's allow list is dropped in silence: the entity never
    appears and nothing logs a refusal. This reads the kinds out of the files themselves."""
    by_target = {
        loc["target"]: loc for loc in _container_locations() if loc["type"] == "file"
    }
    for directory in CATALOGUE_DIRS:
        source = ROOT / "backstage" / directory / "catalog-info.yaml"
        if not source.is_file():
            continue
        held = {d["kind"] for d in yaml.safe_load_all(source.read_text()) if d}
        allowed = set(
            by_target[f"/estate/{directory}/catalog-info.yaml"]["rules"][0]["allow"]
        )
        assert held <= allowed, (
            f"backstage/{directory}/catalog-info.yaml holds {sorted(held - allowed)}, "
            f"which the deployed config drops in silence"
        )


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

"""The catalogue page was showing Component + Owned only.

plugin-catalog 2.0.8 defaults catalog-filter:catalog/kind to component and
catalog-filter:catalog/list to owned. Git holds hundreds of Resource, System,
Template, Group and Domain entities that then exist in the API and flash behind
the table. Official NFS config pages the catalog API and opens on Everything.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "backstage" / "app-config.yaml"


def _extensions():
    ext = {}
    for row in yaml.safe_load(CFG.read_text())["app"]["extensions"]:
        if isinstance(row, dict):
            ext.update(row)
    return ext


def test_the_catalogue_opens_on_everything_not_owned_components():
    ext = _extensions()
    listing = ext["catalog-filter:catalog/list"]["config"]["initialFilter"]
    kind = ext["catalog-filter:catalog/kind"]["config"]["initialFilter"]
    assert listing == "all", listing
    assert kind in ("", None), kind


def test_the_catalogue_pages_the_catalog_api():
    page = _extensions()["page:catalog"]["config"]["pagination"]
    assert page["mode"] == "cursor", page
    assert int(page["limit"]) >= 20, page
    path = _extensions()["page:catalog"]["config"].get("path")
    assert path in (None, "/catalog"), path


def test_git_holds_more_than_components():
    """Receipt for the flash: the files the API ingests are not only Component."""
    kinds = {}
    files = [
        ROOT / "catalog" / "catalog-info.yaml",
        ROOT / "backstage" / "platform" / "catalog-info.yaml",
        ROOT / "backstage" / "org" / "catalog-info.yaml",
        ROOT / "backstage" / "founder" / "catalog-info.yaml",
        ROOT / "backstage" / "examples" / "org.yaml",
    ]
    files += list((ROOT / "backstage" / "templates").rglob("template.yaml"))
    n = 0
    for path in files:
        if not path.exists():
            continue
        for doc in yaml.safe_load_all(path.read_text()):
            if not doc or not doc.get("kind"):
                continue
            n += 1
            kinds[doc["kind"]] = kinds.get(doc["kind"], 0) + 1
    assert n >= 100, n
    assert kinds.get("Component", 0) < n, kinds
    assert kinds.get("System", 0) > 0 and kinds.get("Group", 0) > 0, kinds

"""A visitor must operate the portal without a Backstage glossary.

The menu, the home toolkit and the English overlay never lead with Scaffolder,
TechDocs or Software Catalog. Buyer doors come first; operator doors sit below the divider, one click each.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAV = ROOT / "backstage/packages/app/src/modules/nav/EstateNav.tsx"
APP = ROOT / "backstage/app-config.yaml"
WORDS = ROOT / "backstage/packages/app/src/modules/i18n/words.ts"


def nav_items():
    rows = re.findall(
        r"\{\s*title:\s*'([^']+)',\s*to:\s*'([^']+)',\s*icon:\s*(\w+)\s*\}",
        NAV.read_text(),
    )
    assert rows, "no nav items parsed"
    return [{"title": t, "to": to, "icon": icon} for t, to, icon in rows]


def test_a_visitor_sees_catalogue_health_docs_and_you_first():
    titles = [i["title"] for i in nav_items()]
    assert titles[:5] == ["Home", "Catalogue", "Health", "Docs", "You"], titles
    assert "Create" in titles and "Find" in titles


def test_the_toolkit_matches_the_menu():
    ext = {}
    for row in yaml.safe_load(APP.read_text())["app"]["extensions"]:
        if isinstance(row, dict):
            ext.update(row)
    tools = ext["home-page-widget:home/toolkit"]["config"]["tools"]
    assert [(t["label"], t["url"]) for t in tools] == [
        (i["title"], i["to"]) for i in nav_items()
    ]


def test_the_home_grid_is_not_empty_vendor_cards():
    ext = {}
    for row in yaml.safe_load(APP.read_text())["app"]["extensions"]:
        if isinstance(row, dict):
            ext.update(row)
    components = [w["component"] for w in ext["page:home"]["config"]["defaultConfig"]]
    assert components[0] == "HomePageSearchBar"
    assert "HomePageToolkit" in components
    for empty in (
        "HomePageStarredEntities",
        "HomePageRecentlyVisited",
        "HomePageMostVisited",
    ):
        assert empty not in components, empty

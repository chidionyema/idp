"""crew#612: every nav door opens a real page, and no two doors look the same.

The class of mistake (found by the founder, 2026-08-31): the sidebar linked to
/create while the scaffolder plugin was never wired into the app, so the door
answered 404; two nav items shared the gear icon so they read as one; and two
items pointed at hash fragments of a home layout that no longer exists. A nav
entry is a promise — this test refuses a door whose page is not wired, a door
that looks like another, and a door that points at a layout anchor instead of a
route. It also refuses an icon import nothing uses, which is how the duplicate
gear survived its own fix.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backstage/packages/app/src/App.tsx"
NAV = ROOT / "backstage/packages/app/src/modules/nav/EstateNav.tsx"
CONFIG = ROOT / "backstage/app-config.yaml"


def nav_items() -> list[dict[str, str]]:
    rows = re.findall(
        r"\{\s*title:\s*'([^']+)',\s*to:\s*'([^']+)',\s*icon:\s*(\w+)\s*\}",
        NAV.read_text(),
    )
    assert rows, "no nav items parsed from EstateNav.tsx; the NAV shape moved"
    return [{"title": t, "to": to, "icon": icon} for t, to, icon in rows]


APP_CONFIG = ROOT / "backstage/app-config.yaml"
HOME_MODULE = ROOT / "backstage/packages/app/src/modules/home/homeModule.tsx"


def test_the_front_page_is_backstage_own_home_page_and_its_toolkit_is_the_menu():
    """ "/" is @backstage/plugin-home's own page. Widgets come from the plugin; the drag board
    does not (founder 2026-09-03). The toolkit is the ten menu doors in the same order."""
    import yaml

    app = APP.read_text()
    assert "from '@backstage/plugin-home/alpha'" in app and re.search(
        r"^\s+homePlugin,$", app, re.M
    ), "App.tsx does not load Backstage's home plugin; page:home would be undefined"
    module = HOME_MODULE.read_text()
    layout = (
        ROOT / "backstage/packages/app/src/modules/home/homeLayout.tsx"
    ).read_text()
    code = lambda src: re.sub(r"//.*", "", src)
    assert not re.search(r"path:\s*'/'", module), (
        "modules/home still defines a page at '/', which overrides page:home"
    )
    assert "HomePageLayoutBlueprint.make(" in module, (
        "the home plugin has no custom layout wired"
    )
    assert "CustomHomepageGrid" not in code(
        module
    ) and "CustomHomepageGrid" not in code(layout), (
        "the drag-and-resize board is back on the front page"
    )
    assert "<Header" in layout and (
        'to="/create"' in layout or 'href="/create"' in layout
    ), "Today has no header and no Create action"
    nav = NAV.read_text()
    assert "SidebarGroup" not in code(nav), (
        "a SidebarGroup of one door makes hover a second click"
    )
    assert "SidebarSearchModal" in nav and "keydown" in nav, (
        "Find is not Backstage's search modal, or Cmd+K is missing"
    )
    ext = {}
    for row in yaml.safe_load(APP_CONFIG.read_text())["app"]["extensions"]:
        ext.update(row)
    grid = ext["page:home"]["config"]
    assert grid["path"] == "/", "page:home is not served at /"
    components = [w["component"] for w in grid["defaultConfig"]]
    assert components[0] == "HomePageSearchBar" and "HomePageToolkit" in components, (
        components
    )
    assert grid["defaultConfig"][0].get("deletable") is False, (
        "the search bar can be deleted from the page"
    )
    tools = ext["home-page-widget:home/toolkit"]["config"]["tools"]
    assert [(t["label"], t["url"]) for t in tools] == [
        (i["title"], i["to"]) for i in nav_items()
    ], (
        "the toolkit on the front page and the menu list different doors or a different order"
    )
    visit_cards = {"HomePageRecentlyVisited", "HomePageMostVisited"} & set(components)
    tracking = (
        ext.get("api:home/visits") is True
        and ext.get("app-root-element:home/visit-listener") is True
    )
    if visit_cards:
        assert tracking, (
            "Recently visited and Most visited are on the grid with visit tracking switched off"
        )
    else:
        assert not tracking, (
            "visit tracking stores every visit in the browser and no card on the page reads it"
        )

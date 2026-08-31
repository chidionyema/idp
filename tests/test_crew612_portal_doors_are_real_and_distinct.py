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


def test_no_door_is_a_hash_jump():
    for item in nav_items():
        assert "/#" not in item["to"], (
            f"nav item {item['title']!r} points at layout anchor {item['to']!r}; "
            "link the real route, a scroll position is not a page"
        )


def test_no_two_doors_share_an_icon():
    icons = [i["icon"] for i in nav_items()]
    dupes = {icon for icon in icons if icons.count(icon) > 1}
    assert not dupes, (
        f"nav icons used twice: {sorted(dupes)}; each door reads as itself"
    )


def test_no_two_doors_share_a_route():
    routes = [i["to"] for i in nav_items()]
    dupes = {r for r in routes if routes.count(r) > 1}
    assert not dupes, f"nav routes used twice: {sorted(dupes)}"


def test_every_nav_door_has_its_page_wired():
    """The doors this fix added exist, and their pages are wired into the app."""
    routes = {i["to"] for i in nav_items()}
    app = APP.read_text()
    for route, plugin in [
        ("/create", "scaffolderPlugin"),
        ("/catalog-graph", "catalogGraphPlugin"),
    ]:
        assert route in routes, f"the {route} door is missing from the nav"
        assert plugin in app, (
            f"{plugin} is not wired in App.tsx while the nav links {route}; "
            "that door answers 404"
        )


def test_every_imported_icon_is_used():
    src = NAV.read_text()
    imported = re.findall(r"import (\w+Icon) from '@material-ui/icons/", src)
    used = {i["icon"] for i in nav_items()}
    dead = [icon for icon in imported if icon not in used]
    assert not dead, f"icon imports nothing uses: {dead}"


def test_the_portal_is_not_branded_as_the_store():
    """The portal is the estate portal; Mumchimp is the store it runs, not its name."""
    cfg = CONFIG.read_text()
    for line in cfg.splitlines():
        if re.match(r"\s*(title|name):", line):
            assert "Mumchimp" not in line, (
                f"portal branded as the store: {line.strip()}"
            )

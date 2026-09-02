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
    # An icon counts as used when the file body names it anywhere but its import line: the
    # menu button's MenuIcon is used in JSX, not in the NAV table (2026-09-01, phone menu).
    src = NAV.read_text()
    imported = re.findall(r"import (\w+Icon) from '@material-ui/icons/", src)
    body = re.sub(r"^import .*$", "", src, flags=re.M)
    dead = [icon for icon in imported if not re.search(rf"\b{icon}\b", body)]
    assert not dead, f"icon imports nothing uses: {dead}"


def test_the_phone_gets_a_menu_that_slides_in_from_the_left():
    """Founder, 2026-09-01, on his phone: "where the fuck is the menu"; "why would someone scroll
    to bottom of page to see menu". Backstage folds its sidebar into a bottom bar under 600px.
    The nav now switches on that same breakpoint to a Material Drawer anchored left, opened by
    a button a screen reader calls "Open menu", listing every door in NAV in order."""
    src = NAV.read_text()
    assert "useMediaQuery(theme.breakpoints.down('xs'))" in src, (
        "the phone switch is not Backstage's own xs breakpoint"
    )
    assert re.search(r"<Drawer\s+anchor=\"left\"", src), (
        "the phone menu is not a Drawer anchored left"
    )
    assert (
        "aria-label={`Open ${PHONE_MENU_LABEL.toLowerCase()}`}" in src
        and "PHONE_MENU_LABEL = 'Menu'" in src
    ), "the menu button has no spoken name; the drill opens it by that name (R53)"
    phone = src.split("const PhoneNav")[1].split("const DesktopNav")[0]
    assert "NAV.map(" in phone and "component={Link}" in phone, (
        "the drawer does not list the NAV doors as links"
    )
    assert "onClose={() => setOpen(false)}" in phone, (
        "the drawer does not close on the backdrop or Escape"
    )


APP_CONFIG = ROOT / "backstage/app-config.yaml"
HOME_MODULE = ROOT / "backstage/packages/app/src/modules/home/homeModule.tsx"


def test_the_front_page_is_backstage_own_home_page_and_its_toolkit_is_the_menu():
    """Founder, 2026-09-01: "use Backstage templates", "our UI and design skills are shit", "so
    don't bother". "/" is @backstage/plugin-home's own page: the app loads the plugin, this
    repository defines no page at "/", the grid is seeded from app-config.yaml with the search
    bar and the toolkit, and the toolkit is the ten menu doors in the same order."""
    import yaml

    app = APP.read_text()
    assert "from '@backstage/plugin-home/alpha'" in app and re.search(
        r"^\s+homePlugin,$", app, re.M
    ), "App.tsx does not load Backstage's home plugin; page:home would be undefined"
    module = HOME_MODULE.read_text()
    assert not re.search(r"path:\s*'/'", module), (
        "modules/home still defines a page at '/', which overrides page:home"
    )
    assert (
        "HomePageLayoutBlueprint.make(" in module
        and "CustomHomepageGrid" in module
        and "<Header " in module
    ), (
        "the home layout is not the documented Page/Header/Content/CustomHomepageGrid template"
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
    assert (
        ext.get("api:home/visits") is True
        and ext.get("app-root-element:home/visit-listener") is True
    ), (
        "Recently visited and Most visited are on the grid with visit tracking switched off"
    )


def test_the_portal_is_not_branded_as_the_store():
    """The portal is the estate portal; Mumchimp is the store it runs, not its name."""
    cfg = CONFIG.read_text()
    for line in cfg.splitlines():
        if re.match(r"\s*(title|name):", line):
            assert "Mumchimp" not in line, (
                f"portal branded as the store: {line.strip()}"
            )


def test_the_phone_drill_reads_door_names_from_the_nav_source():
    """2026-09-02: PR #1130 renamed four doors to plain English and bin/idp-login-drill kept
    a hardcoded list of the old names, so the drill failed a healthy live page ('the phone
    menu opened without these doors'). The drill must parse EstateNav.tsx for its door names
    and may hold no door title as a literal, so a rename cannot split page and drill again."""
    drill = (ROOT / "bin/idp-login-drill").read_text()
    assert "EstateNav.tsx" in drill, (
        "the drill no longer reads the nav source for door names"
    )
    for item in nav_items():
        quoted = (f"'{item['title']}'", f'"{item["title"]}"')
        assert not any(q in drill for q in quoted), (
            f"door name {item['title']!r} is hardcoded in bin/idp-login-drill; a rename in "
            "EstateNav.tsx would break the drill again"
        )

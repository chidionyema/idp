"""crew#459 / crew#301: the login drill names which portal the cluster serves.

On 2026-08-29 the branded portal (idp#747) merged at 08:17Z and the login-drill stayed green for
every run after it -- and nothing in the drill could say whether the cluster was serving that
build or the image from before it. A drill that grades a page without naming the build cannot
catch a stalled rollout (the crew#301 incident) and cannot prove a merge landed (LAW 17).

The polished app ships a branded manifest (`name: Mumchimp estate`) and `/icon.svg`; the vendor
build ships `name: Backstage` and no icon. The drill now reads both with the signed-in session,
prints a `build` row, and is red on the vendor manifest. These tests pin that fence to the file.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin" / "idp-login-drill"
MANIFEST = ROOT / "backstage" / "packages" / "app" / "public" / "manifest.json"
ICON = ROOT / "backstage" / "packages" / "app" / "public" / "icon.svg"


def _src() -> str:
    return DRILL.read_text()


def test_the_drill_prints_a_build_row_from_the_served_manifest_and_icon():
    src = _src()
    assert 'page.request.get(f"{HOME}/manifest.json?drill={int(time.time())}"' in src, "the manifest is read past the edge cache (run 33245245766)"
    assert 'page.request.get(f"{HOME}/icon.svg")' in src
    assert re.search(r'print\(f"build   login-drill  the portal serves manifest name', src)


def test_a_vendor_manifest_is_red_not_a_note():
    src = _src()
    m = re.search(r'if mf_name == "Backstage":\s*\n\s*fail\("build"', src)
    assert m, "the vendor manifest name must call fail(), a printed row alone is silent green"
    assert re.search(r'if ic_status != 200:\s*\n\s*fail\("build"', src)


def test_the_branded_build_on_main_is_what_the_fence_expects():
    name = json.loads(MANIFEST.read_text())["name"]
    assert name != "Backstage", "main ships the vendor manifest; the drill would be red on a correct rollout"
    assert ICON.is_file()


def test_the_verdict_line_carries_the_build_name():
    assert "portal build '{mf_name}'" in _src()


HOME = ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home" / "EstateHome.tsx"


def test_incident_run_33244316874_the_drill_counts_the_rows_the_home_page_draws():
    """08:56Z 2026-08-29: the polished home drew 29 rows, the drill counted 0 'Catalogue entry'
    links. The drill counts the surface-<name> test id, and every renderer in EstateHome.tsx
    must carry it."""
    src = _src()
    assert "page.locator(\"[data-testid^='surface-']\").count()" in src
    assert "a:has-text('Catalogue entry')" not in src, "the deep-link count is the selector that read 0 of 29"
    home = HOME.read_text()
    # crew#459 redesign: one renderer (DoorRow) draws every door; it must carry the id, and the
    # empty state must carry no-surfaces, the drill's other selector.
    assert home.count("data-testid={`surface-${entity.metadata.name}`}") >= 1, "the door renderer carries the test id"
    assert 'data-testid="no-surfaces"' in home, "the empty state carries no-surfaces"


def test_incident_run_33245245766_the_manifest_is_read_past_the_edge_cache():
    """/icon.svg answered from the new build while /manifest.json came back cached as the vendor
    one. The drill must bust the cache and print the edge's cache verdict on the row."""
    src = _src()
    assert '"Cache-Control": "no-cache"' in src
    assert 'cf-cache-status' in src
    assert "(edge cache: {mf_cache})" in src

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
    assert 'page.request.get(f"{HOME}/manifest.json")' in src
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

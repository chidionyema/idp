"""Incident test (rung 4), crew#307: /catalog was a client-side 404 for the founder and the
login drill graded the shell, not the page.

Rule 1: no dynamic-plugin page override may put another page at "/catalog" or move the
catalog off it (the 2026-08-26 override served the catalog at "/", so /catalog 404'd).
Rule 2: the drill grades every published path on answering: it loads, is not a client-side
404 inside the shell, and throws no error (founder 2026-09-03: never on wording). Executes
docs/prose/front-door-login-drill-live.feature scenario
"Every published path answers (crew#307)".
"""
import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_incident_crew307_catalog_stays_at_catalog():
    """page:catalog may set pagination and filters; it must not move the path off /catalog."""
    import yaml

    cfg_path = ROOT / "backstage" / "app-config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    for row in cfg["app"]["extensions"]:
        if not isinstance(row, dict) or "page:catalog" not in row:
            continue
        page = row["page:catalog"] or {}
        path = (page.get("config") or {}).get("path")
        assert path in (None, "/catalog"), (
            f"page:catalog moved /catalog to {path!r}; crew#307"
        )


def test_incident_crew307_drill_grades_every_published_path():
    src = (ROOT / "bin" / "idp-login-drill").read_text()
    block = re.search(r"PUBLISHED = \((.*?)\n    \)", src, re.S)
    assert block, "drill lost its PUBLISHED table"
    published = ast.literal_eval("(" + block.group(1) + ")")
    assert len(published) >= 9
    for path in published:
        assert isinstance(path, str) and re.fullmatch(r"[a-z][a-z-]*", path), path
    assert "catalog" in published
    assert "published paths broken" in src


def test_incident_crew307_oke_tag_is_orderable():
    """The OKE overlay pins an orderable main-<run>-<sha> tag (features/hard_execution_chain.feature).

    Flux ImagePolicy (platform/image-automation/backstage.yaml) only orders tags matching
    ^main-(?P<run>[0-9]+)-[0-9a-f]{40}$. A bare sha pin is invisible to it, so the automation
    can never move a bare pin and the catalogue fix never rolls (crew#307, 2026-08-26).
    """
    import re
    from pathlib import Path

    text = Path(__file__).resolve().parents[1].joinpath(
        "platform/backstage/overlays/oke/kustomization.yaml").read_text()
    m = re.search(r"newTag:\s*(\S+)\s*#\s*\{\"\$imagepolicy\"", text)
    assert m, "backstage newTag with the $imagepolicy marker is missing"
    assert re.fullmatch(r"main-[0-9]+-[0-9a-f]{40}", m.group(1)), m.group(1)


def test_incident_crew307_broken_path_row_says_what_rendered():
    """A broken published path prints the page text (features/hard_execution_chain.feature).

    docs and create stayed broken after the rollout and the log could not say whether the
    plugin never loaded or the locator drifted (crew#307, 2026-08-26).
    """
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath("bin/idp-login-drill").read_text()
    assert "page says: {seen}; js errors: {errs}" in src


def test_incident_crew307_material_table_keeps_its_own_uuid():
    """Run 33005225790: /catalog and /docs rendered `TypeError: Cannot read properties of
    undefined (reading 'v4')` in module-material-table. The global `uuid ^11.1.1` resolution
    (idp#65) forced @material-table/core off uuid 3, whose default export it needs in the
    browser bundle. The scoped rule must exist and come before the global one: yarn applies
    the first matching resolution."""
    import json
    pkg = json.load(open(ROOT / "backstage" / "package.json"))
    keys = list(pkg["resolutions"])
    assert "@material-table/core/uuid" in keys
    assert keys.index("@material-table/core/uuid") < keys.index("uuid")
    assert pkg["resolutions"]["@material-table/core/uuid"].startswith("^3.")
    lock = (ROOT / "backstage" / "yarn.lock").read_text()
    assert '"uuid@npm:^3.4.0":' in lock


def test_incident_crew307_no_drill_row_grades_wording():
    """Founder 2026-09-03: copy moves all the time and a checker pinning it broke a working
    page (#1191). The drill grades a path on answering; no row carries expected text."""
    src = (ROOT / "bin" / "idp-login-drill").read_text()
    block = re.search(r"PUBLISHED = (\((?:.|\n)*?\n    \))", src)
    assert block, "PUBLISHED tuple not found"
    assert "text=" not in block.group(1)
    assert "must_see" not in src

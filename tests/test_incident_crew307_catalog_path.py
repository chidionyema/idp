"""Incident test (rung 4), crew#307: /catalog was a client-side 404 for the founder and the
login drill graded the shell, not the page.

Rule 1: no dynamic-plugin page override may put another page at "/catalog" or move the
catalog off it (the 2026-08-26 override served the catalog at "/", so /catalog 404'd).
Rule 2: the drill grades every published path on text of its own, so a rendered shell
cannot pass for a page. Executes docs/prose/front-door-login-drill-live.feature scenario
"Every published path renders its own content, not the shell around it (crew#307)".
"""
import ast
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_incident_crew307_catalog_stays_at_catalog():
    cfg = (ROOT / "backstage" / "app-config.yaml").read_text()
    assert not re.search(r"^\s*- page:catalog:", cfg, re.M), "page:catalog override moves /catalog; crew#307"


def test_incident_crew307_drill_grades_every_published_path():
    src = (ROOT / "bin" / "idp-login-drill").read_text()
    block = re.search(r"PUBLISHED = \((.*?)\n    \)", src, re.S)
    assert block, "drill lost its PUBLISHED table"
    published = ast.literal_eval("(" + block.group(1) + ")")
    assert len(published) >= 9
    for path, must_see in published:
        assert must_see.startswith("text=") and len(must_see) > len("text=x"), path
    assert "catalog" in dict(published)
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

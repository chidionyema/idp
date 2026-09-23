"""Incident crew#693 (2026-08-30 17:01Z to 2026-08-31): the shop served an eight-hour-old build.

prospector#793 merged, `container images` pushed `prospector-store-web:main-85-0299e2c4` to ghcr at
21:01:04Z, and the cluster kept running `main-73`. Measured at 22:02:32Z: the live home page linked
77 packs and referenced 0 pack pictures, and `/pack/d6ce3ca2ff304cda.jpg` answered 404. Every
instrument in the estate read green -- flux reconciled what git held, the pods were Ready, the
login drill signed in -- because no drill in this repository ever opened the shop. The founder
found it by looking at the site.

`bin/idp-storefront-drill` is the drill that finds it next time. These are the three properties it
must keep, each one a way the drill could pass while the shop is broken:

  1. zero pack pictures referenced is a FAIL, never a pass on an empty list. That is the exact
     shape of the outage, and it is also the estate's most repeated defect class (silent-green,
     four on the incident ledger): a row that grades a list never checks whether the list is empty.
  2. the shop's host is read from clusters/oke/estate-config.yaml, never typed (LAW 46).
  3. nothing about layout. A picture that loads and a page that answers are features; where they
     sit on the screen is not a drill's business (R53, founder 2026-08-29: "UI is volatile").
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin" / "idp-storefront-drill"
CATALOGUE = ROOT / "drills" / "catalogue.yaml"


def _module():
    loader = importlib.machinery.SourceFileLoader(
        "storefront_drill_crew693", str(DRILL)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


# A home page exactly as the shop served it during the outage: packs listed, no pictures at all.
DURING_THE_OUTAGE = (
    '<a class="htile" href="/pack/08b22037fc2afc07">one</a>'
    '<a class="htile" href="/pack/08dbe23f7be7af97">two</a>'
)
# The same page from the build the release was trying to ship, measured on the local production
# build at 2026-08-31: every tile carries its cover.
AFTER_THE_RELEASE = (
    '<a class="htile" href="/pack/08b22037fc2afc07">'
    '<img class="cover" src="/pack/08b22037fc2afc07.jpg" alt="" /></a>'
    '<a class="htile" href="/pack/08dbe23f7be7af97">'
    '<img class="cover" src="/pack/08dbe23f7be7af97.jpg" alt="" /></a>'
)


@pytest.fixture
def drill(monkeypatch):
    module = _module()
    monkeypatch.setattr(module, "zone", lambda: "shop.example")
    return module


def _run(module, monkeypatch, home: str, picture_status: int = 200) -> tuple[int, str]:
    def fetch(url: str):
        if url.endswith(".jpg"):
            return (
                picture_status,
                "image/jpeg",
                b"\xff\xd8\xff" if picture_status == 200 else b"",
            )
        return 200, "text/html; charset=utf-8", home.encode()

    monkeypatch.setattr(module, "fetch", fetch)
    module.failures = 0
    printed: list[str] = []
    monkeypatch.setattr(
        "builtins.print", lambda *a, **k: printed.append(" ".join(str(x) for x in a))
    )
    code = module.main()
    return code, "\n".join(printed)


def test_zero_pack_pictures_is_a_fail_not_a_pass_on_an_empty_list(drill, monkeypatch):
    code, out = _run(drill, monkeypatch, DURING_THE_OUTAGE)
    assert code == 1, f"the drill passed the outage it exists to catch:\n{out}"
    assert re.search(r"^FAIL +pack-pictures", out, re.M), out
    assert "references 0 pack pictures" in out, out


def test_the_build_that_was_being_shipped_makes_every_row_green(drill, monkeypatch):
    code, out = _run(drill, monkeypatch, AFTER_THE_RELEASE)
    assert code == 0, (
        f"a drill that can only ever be red is an alarm, not a drill:\n{out}"
    )
    assert re.search(r"^ok +pack-pictures", out, re.M), out


def test_a_picture_the_page_names_and_the_shop_does_not_serve_is_a_fail(
    drill, monkeypatch
):
    code, out = _run(drill, monkeypatch, AFTER_THE_RELEASE, picture_status=404)
    assert code == 1, out
    assert "404" in out, out


def test_the_shop_host_is_read_from_the_estate_config_never_typed():
    source = DRILL.read_text()
    body = source.split('"""', 2)[
        2
    ]  # the docstring quotes the incident and names the host once
    assert "mumchimp" not in body, (
        "LAW 46: the zone is read from clusters/oke/estate-config.yaml"
    )
    assert "ESTATE_ZONE" in body


def test_the_drill_grades_features_and_never_layout():
    source = DRILL.read_text().lower()
    for word in (
        "data-testid",
        "queryselector",
        "css",
        "pixel",
        "font",
        "colour",
        "stylesheet",
    ):
        assert word not in source, f"R53: a drill may not grade look and feel ({word})"


def test_the_catalogue_entry_names_this_workflow_and_its_cron_verbatim():
    row = [
        d
        for d in yaml.safe_load(CATALOGUE.read_text())["drills"]
        if d["name"] == "storefront-smoke"
    ]
    assert row, (
        "the drill is not in drills/catalogue.yaml, so bin/idp-verify never grades its freshness"
    )
    entry = row[0]
    workflow = ROOT / ".github" / "workflows" / entry["workflow"]
    cron = re.findall(r"- cron: \"([^\"]+)\"", workflow.read_text())
    assert entry["schedule"] in cron, (
        f"{entry['schedule']} is not a cron line in {entry['workflow']}"
    )
    assert entry["owner"], "crew#684 CP3: a drill with no owner is refused"

"""idp#1141 (2026-09-02): the login drill graded a menu rename as a 6-hour outage.

The class of mistake: a third hardcoded copy of the door names lived in
bin/idp-login-drill, so when idp#1130 renamed the doors in the one guarded
source (backstage/app-config.yaml, held equal to the menu by
tests/test_crew612_portal_doors_are_real_and_distinct.py) the drill kept
asserting the old words: Today, What we run, Ops, How-to. One place for every
name (R70). This test refuses the drill ever growing its own door list again,
and proves the parse the drill now uses yields real, distinct doors.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DRILL = ROOT / "bin" / "idp-login-drill"
CONFIG = ROOT / "backstage" / "app-config.yaml"
TOOLKIT_KEY = "home-page-widget:home/toolkit"


def toolkit_labels() -> list[str]:
    rows = yaml.safe_load(CONFIG.read_text())["app"]["extensions"]
    row = next(r for r in rows if isinstance(r, dict) and TOOLKIT_KEY in r)
    return [t["label"] for t in row[TOOLKIT_KEY]["config"]["tools"]]


def test_drill_reads_the_doors_from_app_config_not_a_local_copy():
    src = DRILL.read_text()
    assert TOOLKIT_KEY in src, (
        "bin/idp-login-drill no longer reads the toolkit from app-config; "
        "the drill must grade the one guarded door list, never its own copy"
    )
    for stale in ("What we run", "How-to"):
        assert stale not in src, (
            f"bin/idp-login-drill still names the pre-#1130 door {stale!r}; "
            "a hardcoded door name here is the idp#1141 outage again"
        )


def test_the_toolkit_parse_the_drill_uses_yields_real_distinct_doors():
    labels = toolkit_labels()
    assert len(labels) >= 8, (
        f"toolkit lists only {labels}; the phone menu would be empty"
    )
    assert len(labels) == len(set(labels)), f"duplicate door labels: {labels}"
    assert all(isinstance(x, str) and x.strip() for x in labels), labels

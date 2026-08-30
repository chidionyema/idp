"""crew#684, 2026-08-30 07:0xZ: two fixes rolled (idp#957 Host header, idp#962 enrol on pod start)
and the Ops tile still read "Healthchecks answered 401". Nothing in the estate could say which
layer refused: the file the portal holds, the file Healthchecks holds, the DB row enrol wrote,
or the request itself. `healthchecks-door` grades every one from inside the two pods (LAW 28:
a row named after the property the caller needs; LAW 15: two pods, one answer)."""

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "bin" / "idp-oke-break-glass"
WORKFLOW = ROOT / ".github" / "workflows" / "oke-check.yml"
BUTTON = (
    ROOT / "backstage" / "templates" / "founder-actions" / "oke-check" / "template.yaml"
)
APP_CONFIG = ROOT / "backstage" / "app-config.container.yaml"


def test_healthchecks_door_is_listed_wired_and_offered():
    listed = subprocess.run(
        [str(PLAYBOOK), "--list"], capture_output=True, text=True
    ).stdout.split()
    assert "healthchecks-door" in listed
    body = PLAYBOOK.read_text()
    assert "healthchecks-door) pb_healthchecks_door ;;" in body
    offered = yaml.safe_load(WORKFLOW.read_text())[True]["workflow_dispatch"]["inputs"][
        "playbook"
    ]["options"]
    assert "healthchecks-door" in offered
    assert (
        "healthchecks-door"
        in yaml.safe_load(BUTTON.read_text())["spec"]["parameters"][0]["properties"][
            "playbook"
        ]["enum"]
    )


def test_every_layer_between_the_portal_and_healthchecks_has_a_row():
    fn = (
        PLAYBOOK.read_text()
        .split("pb_healthchecks_door() {", 1)[1]
        .split("\n}\n", 1)[0]
    )
    for row in (
        "portal-key-mounted",
        "hc-key-mounted",
        "keys-agree",
        "enrol-log",
        "key-enrolled",
        "door-opens",
    ):
        assert re.search(rf"^\s*(step|show_redacted) {row} ", fn, re.M), (
            f"row {row} missing"
        )
    # hashes and lengths only: a key value never reaches a run log (R49)
    assert "sha256sum" in fn and "cat $pk" not in fn and "cat $hk" not in fn


def test_door_opens_sends_exactly_the_portal_proxys_headers():
    fn = PLAYBOOK.read_text().split("pb_healthchecks_door() {", 1)[1]
    cfg = yaml.safe_load(APP_CONFIG.read_text())["proxy"]["endpoints"]["/healthchecks"]
    assert cfg["target"] in fn, "the row must call the target the proxy calls"
    assert cfg["headers"]["X-Api-Key"]["$file"] in fn
    assert "HEALTHCHECKS_HOST" in fn and "HEALTHCHECKS_HOST" in cfg["headers"]["Host"]

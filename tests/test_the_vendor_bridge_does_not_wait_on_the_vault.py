"""The vendor bridge is applied without waiting for the vault to hold every key it names.

platform/vendors renders one ExternalSecret per key the estate expects a person to put in
Bitwarden. Some are optional, and some (PUBLIC_SERVER_URL) are written later by a deploy step,
so a correct render always has red ExternalSecrets in it. With Helm's wait on, that red failed
the release: 5m timeout, 3 retries, stalled, and on 2026-10-03 suspended by hand -- the merged
fix for the optional Twilio fields (#5928) was packaged and never applied for nine days. Each
ExternalSecret reports its own Ready condition; the release must not borrow it.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
RELEASE = ROOT / "platform" / "human-vault-bridge" / "helmrelease.yaml"


def test_install_and_upgrade_do_not_wait() -> None:
    spec = yaml.safe_load(RELEASE.read_text())["spec"]
    assert spec["install"].get("disableWait") is True
    assert spec["upgrade"].get("disableWait") is True


def test_the_release_is_not_suspended_in_git() -> None:
    assert not yaml.safe_load(RELEASE.read_text())["spec"].get("suspend")

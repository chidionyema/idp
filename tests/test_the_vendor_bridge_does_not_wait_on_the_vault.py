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


def _bridge():
    import shutil
    import subprocess

    out = subprocess.run(
        [
            shutil.which("helm") or "helm",
            "template",
            "vb",
            str(ROOT / "platform" / "vendors"),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [
        d for d in yaml.safe_load_all(out) if d and d.get("kind") == "ExternalSecret"
    ]


def test_no_two_external_secrets_write_one_secret() -> None:
    """external-secrets refuses a second writer ("secret is owned by another ExternalSecret"),
    measured live 2026-10-13 when the optional Twilio fields were Merge objects into
    human-twilio: the numbers sat in Bitwarden and never landed."""
    seen: dict = {}
    for d in _bridge():
        key = (d["metadata"]["namespace"], d["spec"]["target"]["name"])
        assert key not in seen, (
            f"{key} written by {seen[key]} and {d['metadata']['name']}"
        )
        seen[key] = d["metadata"]["name"]
    assert ("concierge", "human-twilio-mom-phone-number") in seen

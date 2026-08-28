"""crew#495 CP8 slice 1: the SigNoz admin is provisioned from the vault, never by the sign-up page.

SigNoz >= v0.112 creates one root user at startup when SIGNOZ_USER_ROOT_ENABLED is set and
SIGNOZ_USER_ROOT_EMAIL / _PASSWORD are present. Without them the first visitor to
signoz.${ESTATE_ZONE} registers as the admin. This test holds the chain together: the chart
value map turns the feature on, the HelmRelease takes email and password from the signoz-root
Secret, the ExternalSecret fills that Secret from vault entries, and platform/oci/signoz.tf
writes those entries. No file in git holds the password.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / "platform" / "observability"
TF = ROOT / "platform" / "oci" / "signoz.tf"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _by(path: Path, kind: str, name: str) -> dict:
    for d in _docs(path):
        if d.get("kind") == kind and d["metadata"]["name"] == name:
            return d
    raise AssertionError(f"{path.name}: no {kind}/{name}")


def test_incident_crew495_signoz_root_admin_comes_from_the_vault() -> None:
    values = yaml.safe_load((OBS / "values.yaml").read_text())
    env = values["signoz"]["env"]
    assert env["SIGNOZ_USER_ROOT_ENABLED"] == "true"
    assert "SIGNOZ_USER_ROOT_PASSWORD" not in env, "the password must come from the vault, not git"

    hr = _by(OBS / "signoz.yaml", "HelmRelease", "signoz")
    targets = {
        v["targetPath"]: (v["name"], v["valuesKey"])
        for v in hr["spec"]["valuesFrom"]
        if v.get("kind") == "Secret"
    }
    assert targets["signoz.env.SIGNOZ_USER_ROOT_EMAIL"] == ("signoz-root", "email")
    assert targets["signoz.env.SIGNOZ_USER_ROOT_PASSWORD"] == ("signoz-root", "password")

    es = _by(OBS / "signoz.yaml", "ExternalSecret", "signoz-root")
    assert es["spec"]["target"]["name"] == "signoz-root"
    remote = {d["secretKey"]: d["remoteRef"]["key"] for d in es["spec"]["data"]}
    assert remote == {"email": "signoz-root-email", "password": "signoz-root-password"}

    tf = TF.read_text()
    for entry in remote.values():
        assert f'"{entry}"' in tf, f"{TF.name} does not write vault entry {entry}"
    assert 'resource "random_password" "signoz_root"' in tf


def test_incident_crew495_the_chain_breaks_when_a_link_is_missing() -> None:
    """The must-fail side: the same check over a HelmRelease that names a Secret the ExternalSecret
    does not write refuses, so a renamed entry cannot pass silently."""
    hr = _by(OBS / "signoz.yaml", "HelmRelease", "signoz")
    es = _by(OBS / "signoz.yaml", "ExternalSecret", "signoz-root")
    written = {d["secretKey"] for d in es["spec"]["data"]}
    wanted = {
        v["valuesKey"]
        for v in hr["spec"]["valuesFrom"]
        if v.get("kind") == "Secret" and v["name"] == "signoz-root"
    }
    assert wanted <= written
    broken = wanted | {"api_token"}
    assert not broken <= written, "a key the ExternalSecret never writes must be refused"
    assert re.search(r"SIGNOZ_USER_ROOT_ENABLED", (OBS / "values.yaml").read_text())

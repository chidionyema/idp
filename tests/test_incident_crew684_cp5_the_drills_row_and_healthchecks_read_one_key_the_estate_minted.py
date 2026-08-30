"""crew#684 CP5, founder 2026-08-30 "I need to see everything": the Ops page carries the drills row
and the Healthchecks state. Incident class (R52, crew#742): a read-only API key made in a vendor
console and pasted into a config, or read by the browser. Guard: Terraform mints one value
(healthchecks-ro-key), the Healthchecks enrol step sets it on the project, the portal receives it
only as a mounted file the proxy endpoint adds server-side, and the page names no host and no key.
Fault class: process.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home"
KEY = "healthchecks-ro-key"


def test_one_value_minted_by_terraform_is_read_by_both_rows() -> None:
    tf = (ROOT / "platform" / "oci" / "healthchecks.tf").read_text()
    assert 'resource "random_uuid" "healthchecks_ro_key"' in tf
    assert f'"{KEY}"' in tf and "random_uuid.healthchecks_ro_key.result" in tf
    hc = list(yaml.safe_load_all((ROOT / "platform" / "healthchecks" / "external-secret.yaml").read_text()))
    keys = {d["secretKey"]: d["remoteRef"]["key"] for doc in hc if doc for d in doc["spec"].get("data", [])}
    assert keys.get("RO_KEY") == KEY
    bs = yaml.safe_load((ROOT / "platform" / "backstage" / "overlays" / "oke" / "healthchecks-ro-external-secret.yaml").read_text())
    assert bs["spec"]["data"] == [{"secretKey": "HC_API_KEY_RO", "remoteRef": {"key": KEY}}]
    assert bs["metadata"]["namespace"] == "backstage"


def test_enrol_sets_the_read_only_key_on_the_project() -> None:
    enrol = (ROOT / "platform" / "healthchecks" / "healthchecks.yaml").read_text()
    assert 'project.api_key_readonly = os.environ["RO_KEY"]' in enrol


def test_the_portal_holds_the_key_as_a_file_and_the_page_names_no_host() -> None:
    cfg = yaml.safe_load((ROOT / "backstage" / "app-config.container.yaml").read_text())
    ep = cfg["proxy"]["endpoints"]["/healthchecks"]
    assert ep["allowedMethods"] == ["GET"]
    assert ep["headers"]["X-Api-Key"] == {"$file": "/run/secrets/healthchecks-ro/HC_API_KEY_RO"}
    kz = (ROOT / "platform" / "backstage" / "overlays" / "oke" / "kustomization.yaml").read_text()
    assert "healthchecks-ro-external-secret.yaml" in kz
    assert "mountPath: /run/secrets/healthchecks-ro" in kz and "optional: false" in kz
    hook = (HOME / "useHealthchecks.ts").read_text()
    assert "getBaseUrl('proxy')" in hook and "HC_CHECKS" in hook
    assert "https://" not in hook and "X-Api-Key" not in hook and "svc" not in hook
    ops = (HOME / "Ops.tsx").read_text()
    for tid in ("ops-drills", "ops-healthchecks", "ops-healthchecks-error"):
        assert f'data-testid="{tid}"' in ops, tid

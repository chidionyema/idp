"""Incident 2026-08-30 04:2xZ-04:5xZ, founder: "backstage is down again".

idp#932 (crew#684 CP5) mounted the secret `healthchecks-ro` into the catalogue pod with
`optional: false` while its vault entry (`healthchecks-ro-key`, born in Terraform) waited on the
next apply. The ExternalSecret sat in SecretSyncedError ("could not get secret data from
provider"), the new catalogue pod stayed in ContainerCreating (oke-check run 33292780315,
04:37Z) and the rollout could not finish until the entry existed (run 33293508611, 04:56Z:
synced, 2/2). The tile for a source that cannot be read already says so and the login drill
already grades that sentence red (crew#684 CP6): the loud path exists, so the mount never
needs to stop the pod. Every secret volume on the catalogue Deployment that is fed by an
ExternalSecret whose remote key is minted by Terraform must be optional.
"""

from __future__ import annotations

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "platform" / "backstage" / "overlays" / "oke"
TERRAFORM = ROOT / "platform" / "oci"


def _terraform_minted_keys() -> set[str]:
    """Every quoted map key in platform/oci/*.tf: the vault entries Terraform mints
    (`"healthchecks-ro-key" = random_uuid...` with `secret_name = each.key`)."""
    keys: set[str] = set()
    for tf in TERRAFORM.glob("*.tf"):
        for m in re.finditer(r'^\s*"([a-z0-9-]+)"\s*=', tf.read_text(), re.M):
            keys.add(m.group(1))
    return keys


def _external_secret_targets_minted_by_terraform() -> set[str]:
    minted = _terraform_minted_keys()
    targets: set[str] = set()
    for f in OVERLAY.glob("*.yaml"):
        for doc in yaml.safe_load_all(f.read_text()):
            if not doc or doc.get("kind") != "ExternalSecret":
                continue
            remote = {d["remoteRef"]["key"] for d in doc["spec"].get("data", [])}
            if remote & minted:
                targets.add(doc["spec"]["target"]["name"])
    return targets


def test_a_terraform_minted_secret_mount_is_optional_on_the_catalogue_pod():
    ks = yaml.safe_load((OVERLAY / "kustomization.yaml").read_text())
    targets = _external_secret_targets_minted_by_terraform()
    assert "healthchecks-ro" in targets, "the incident's own secret is the first case"
    seen = set()
    for patch in ks.get("patches", []):
        ops = patch.get("patch")
        if isinstance(ops, str):  # `patch: |` carries the JSON-patch list as text
            ops = yaml.safe_load(ops)
        for op in ops if isinstance(ops, list) else []:
            value = op.get("value") or {}
            secret = value.get("secret") if isinstance(value, dict) else None
            if secret and secret.get("secretName") in targets:
                seen.add(secret["secretName"])
                assert secret.get("optional") is True, (
                    f"{secret['secretName']}: a vault entry that waits on terraform apply must "
                    "never hold the portal's rollout; make the mount optional"
                )
    assert seen == targets, f"mounts not found for {targets - seen}"

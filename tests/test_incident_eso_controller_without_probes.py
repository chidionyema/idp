"""Incident 2026-08-25: Kyverno require-pod-probes refused the external-secrets
controller Deployment (HelmRelease Failed, Flux kustomization stuck on health).
The chart ships livenessProbe/readinessProbe disabled. Rule: the ESO release
enables both. Rung 4 (incident test)."""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _helmrelease() -> dict:
    docs = yaml.safe_load_all((ROOT / "platform/secrets/external-secrets.yaml").read_text())
    return next(d for d in docs if d and d.get("kind") == "HelmRelease")


def test_incident_eso_controller_probes_enabled() -> None:
    values = _helmrelease()["spec"]["values"]
    assert values["livenessProbe"]["enabled"] is True
    assert values["readinessProbe"]["enabled"] is True


def test_cloudflare_token_comes_from_oci_vault_not_sops() -> None:
    d = yaml.safe_load((ROOT / "platform/prospector/cloudflare-external-secret.yaml").read_text())
    assert d["kind"] == "ExternalSecret"
    assert d["spec"]["secretStoreRef"] == {"kind": "ClusterSecretStore", "name": "oci-vault"}
    assert not (ROOT / "platform/prospector/cloudflare.sops.yaml").exists()

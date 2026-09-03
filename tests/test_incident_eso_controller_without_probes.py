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
    d = yaml.safe_load((ROOT / "platform/dns/cloudflare-external-secret.yaml").read_text())
    assert d["kind"] == "ExternalSecret"
    assert d["spec"]["secretStoreRef"] == {"kind": "ClusterSecretStore", "name": "estate-vault"}
    assert not (ROOT / "platform/prospector/cloudflare.sops.yaml").exists()


def test_no_sops_files_remain_under_platform() -> None:
    # crew#227 CP3: the sops-age key goes when the last sops file is gone.
    assert not list(ROOT.glob("platform/**/*.sops.yaml"))


def test_every_platform_external_secret_uses_estate_vault() -> None:
    files = list(ROOT.glob("platform/**/*external-secret.yaml"))
    assert len(files) >= 3
    for f in files:
        # crew#325: a secret file may hold several documents (ExternalSecret + its sibling
        # objects); grade every ExternalSecret in it, and require at least one.
        docs = [d for d in yaml.safe_load_all(f.read_text()) if d]
        externals = [d for d in docs if d.get("kind") == "ExternalSecret"]
        assert externals, f
        for d in externals:
            assert d["spec"]["secretStoreRef"] == {"kind": "ClusterSecretStore", "name": "estate-vault"}, f

def test_no_flux_kustomization_decrypts_with_sops() -> None:
    # crew#227 CP3: with no sops files left, a decryption block is a dangling key reference.
    for f in ROOT.glob("clusters/oke/*.yaml"):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "Kustomization" and str(d.get("apiVersion", "")).startswith("kustomize.toolkit"):
                assert "decryption" not in d["spec"], f

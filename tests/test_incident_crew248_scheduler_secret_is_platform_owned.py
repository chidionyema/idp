"""Incident crew#248: the prospector-scheduler Deployment mounts Secret prospector-engine-env
(optional: false), and nothing on the cluster created that Secret, so the pod could never start.
Rule: the platform owns it, as an ExternalSecret in platform/prospector listed in its
kustomization, pulled from estate-vault under the same key name. Rung 4 (incident test)."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PROSPECTOR = ROOT / "platform/prospector"


def test_incident_crew248_engine_env_secret_is_platform_owned() -> None:
    d = yaml.safe_load((PROSPECTOR / "engine-external-secret.yaml").read_text())
    assert d["kind"] == "ExternalSecret"
    assert d["metadata"] == {"name": "prospector-engine-env", "namespace": "prospector"}
    assert d["spec"]["secretStoreRef"] == {"kind": "ClusterSecretStore", "name": "estate-vault"}
    assert d["spec"]["target"]["name"] == "prospector-engine-env"
    assert d["spec"]["dataFrom"] == [{"extract": {"key": "prospector-engine-env"}}]


def test_every_external_secret_in_platform_prospector_is_applied() -> None:
    # A file kustomize does not list never reaches the cluster.
    listed = set(yaml.safe_load((PROSPECTOR / "kustomization.yaml").read_text())["resources"])
    on_disk = {p.name for p in PROSPECTOR.glob("*external-secret.yaml")}
    assert on_disk <= listed, on_disk - listed

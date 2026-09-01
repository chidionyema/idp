"""The otto-staging token chain holds end to end (control for platform/otto-staging).

The vault entry name, the ExternalSecret mapping and the pod's file-reading wrapper
must agree; if any link drifts, the pod boots with no token and the bot goes silent
with green manifests. This test fails the pull request instead.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(rel: str):
    text = (ROOT / rel).read_text()
    return [d for d in yaml.safe_load_all(text) if d]


def test_external_secret_maps_the_vault_token_to_the_env_key() -> None:
    kinds = [
        d
        for d in _docs("platform/otto-staging/telegram-secret.yaml")
        if d.get("kind") == "ExternalSecret"
    ]
    assert kinds, "telegram-secret.yaml lost its ExternalSecret document"
    row = kinds[0]["spec"]["data"][0]
    assert row["secretKey"] == "OTTO_TELEGRAM_BOT_TOKEN"
    assert row["remoteRef"]["key"] == "otto-staging-telegram"
    assert row["remoteRef"]["property"] == "token"


def test_the_pod_reads_the_mounted_file_and_boots_otto() -> None:
    rel = "platform/otto-staging/deployment.yaml"
    text = (ROOT / rel).read_text()
    assert "/run/secrets/otto-staging-telegram/OTTO_TELEGRAM_BOT_TOKEN" in text, (
        "the wrapper no longer reads the mounted token file"
    )
    assert "otto.boot" in text, "the pod no longer starts otto.boot"
    deployments = [d for d in _docs(rel) if d.get("kind") == "Deployment"]
    assert deployments, "deployment.yaml lost its Deployment document"
    volumes = deployments[0]["spec"]["template"]["spec"]["volumes"]
    assert any(
        v.get("secret", {}).get("secretName") == "otto-staging-telegram"
        for v in volumes
    ), "no volume mounts the otto-staging-telegram secret"


def test_the_drill_catalogue_carries_the_otto_staging_row() -> None:
    text = (ROOT / "drills/catalogue.yaml").read_text()
    assert "name: otto-staging" in text, (
        "drills/catalogue.yaml lost the otto-staging row"
    )

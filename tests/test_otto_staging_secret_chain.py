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
    spec = kinds[0]["spec"]
    assert spec["secretStoreRef"]["name"] == "estate-vault", (
        "the token rides the machine road (founder 2026-09-02 evening): the vault entry "
        "otto-staging-telegram was measured holding fields token+webhook_secret while the "
        "Bitwarden project held nothing and the pod never booted; a human-vault pointer "
        "here reads an entry nobody writes"
    )
    row = spec["data"][0]
    assert row["secretKey"] == "OTTO_TELEGRAM_BOT_TOKEN"
    assert row["remoteRef"]["key"] == "otto-staging-telegram"
    assert row["remoteRef"].get("property") == "token", (
        "the entry is JSON with fields token and webhook_secret; without the property "
        "selector the pod would read the whole JSON blob as its bot token"
    )


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


def test_the_webhook_door_is_locked_at_the_gateway_not_in_the_pod() -> None:
    """Founder edict 2026-09-02: auth is infrastructure physics. The route itself must
    enforce the Telegram secret with an exact header match fed from the vault; if any
    link drifts the gateway either drops every webhook (loud) or the row fails by name
    (loud) -- never an open door."""
    routes = [
        d
        for d in _docs("platform/otto-staging/httproute.yaml")
        if d.get("kind") == "HTTPRoute"
    ]
    assert routes, "httproute.yaml lost its HTTPRoute document"
    route = routes[0]
    assert (route["metadata"].get("annotations") or {}).get(
        "idp.estate/auth"
    ) == "telegram-webhook-secret-token"
    webhook_matches = [
        m
        for r in route["spec"]["rules"]
        for m in r.get("matches", [])
        if m.get("path", {}).get("value") == "/telegram-webhook"
    ]
    assert webhook_matches, "the route lost its /telegram-webhook rule"
    for m in webhook_matches:
        headers = m.get("headers", [])
        assert any(
            h.get("type") == "Exact"
            and h.get("name") == "X-Telegram-Bot-Api-Secret-Token"
            and h.get("value") == "${OTTO_WEBHOOK_SECRET}"
            for h in headers
        ), "the webhook match lost its exact secret-token header match"

    ext = [
        d
        for d in _docs("platform/otto-staging-secret/webhook-substitution.yaml")
        if d.get("kind") == "ExternalSecret"
    ]
    assert ext, "webhook-substitution.yaml lost its ExternalSecret"
    row = ext[0]["spec"]["data"][0]
    assert row["secretKey"] == "OTTO_WEBHOOK_SECRET"
    assert row["remoteRef"]["key"] == "otto-staging-telegram"
    assert row["remoteRef"]["property"] == "webhook_secret"
    assert ext[0]["metadata"]["namespace"] == "flux-system"

    clusters = (ROOT / "clusters/oke/platform.yaml").read_text()
    assert "name: otto-webhook" in clusters, (
        "the otto-staging row no longer substitutes from the otto-webhook Secret"
    )
    assert "name: otto-staging-secret" in clusters, (
        "the otto-staging-secret row left clusters/oke/platform.yaml"
    )

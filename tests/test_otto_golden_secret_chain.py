"""The otto-golden token chain holds end to end (control for platform/otto-golden).

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
        for d in _docs("platform/otto-golden/telegram-secret.yaml")
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
    rel = "platform/otto-golden/deployment.yaml"
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
    assert "name: otto-golden" in text, (
        "drills/catalogue.yaml lost the otto-golden row"
    )


def test_the_webhook_door_is_locked_at_the_gateway_not_in_the_pod() -> None:
    """Founder edict 2026-09-02: auth is infrastructure physics. The route itself must
    enforce the Telegram secret with an exact header match fed from the vault; if any
    link drifts the gateway either drops every webhook (loud) or the row fails by name
    (loud) -- never an open door."""
    routes = [
        d
        for d in _docs("platform/otto-golden/httproute.yaml")
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
        for d in _docs("platform/otto-golden-secret/webhook-substitution.yaml")
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
        "the otto-golden row no longer substitutes from the otto-webhook Secret"
    )
    assert "name: otto-golden-secret" in clusters, (
        "the otto-golden-secret row left clusters/oke/platform.yaml"
    )


def test_the_allowlist_chain_holds_from_vault_to_boot_config() -> None:
    """The mute-bot class (found live 2026-09-03): the boot config shipped as a
    placeholder with no chat_allowlist, otto.boot trusted nobody, and every founder
    message was acked 200 and dropped while every manifest read green. This pins the
    whole chain: the config names an allowlist with a substituted founder chat id, the
    substitution Secret carries that key from the vault, and a broken link fails the
    pull request instead of shipping a mute bot."""
    cms = [
        d
        for d in _docs("platform/otto-golden/config.yaml")
        if d.get("kind") == "ConfigMap"
    ]
    assert cms, "config.yaml lost its ConfigMap document"
    boot = yaml.safe_load(cms[0]["data"]["boot.yaml"])
    allowlist = boot.get("chat_allowlist")
    assert isinstance(allowlist, dict) and allowlist, (
        "boot.yaml carries no chat_allowlist: otto.boot treats every sender as "
        "unrecognised (ack 200, drop, no reply) and the bot is mute with green manifests"
    )
    assert allowlist.get("${OTTO_OPERATOR_CHAT_ID}") == "founder", (
        "the allowlist no longer maps the substituted founder chat id to the founder "
        "principal; a literal chat id here would break LAW 46, a missing row mutes him"
    )

    ext = [
        d
        for d in _docs("platform/otto-golden-secret/webhook-substitution.yaml")
        if d.get("kind") == "ExternalSecret"
    ]
    assert ext, "webhook-substitution.yaml lost its ExternalSecret"
    rows = {r["secretKey"]: r["remoteRef"] for r in ext[0]["spec"]["data"]}
    assert rows.get("OTTO_OPERATOR_CHAT_ID") == {
        "key": "notify-apprise-founder-telegram",
        "property": "chat",
    }, (
        "the substitution Secret no longer carries OTTO_OPERATOR_CHAT_ID from the "
        "founder's telegram vault entry; the ConfigMap would apply with the literal "
        "placeholder and otto.boot refuses a non-integer chat id at startup"
    )

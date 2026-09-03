"""Incident 2026-08-28 (crew#562): two Moonlight pairing PINs expired before a session could type
them into Sunshine's web UI on the founder's Mac. Founder: "it times out because in sending agent
pin and waiting for them to activate". ADR 0009 decision founder-screen-access, three paths on his
tie receipt (5458131885); path 1 is Sunshine + Moonlight with the PIN entered from the portal.

Rule: the portal owns the pairing step end to end, with no hostname, port or credential in code
(LAW 46) and no credential in an environment variable (secrets-not-from-env-vars). Rung 4, one
test per bug; reads files only."""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP = ROOT / "backstage" / "packages" / "app" / "src" / "modules" / "home"
CONFIG = ROOT / "backstage" / "app-config.container.yaml"
OVERLAY = ROOT / "platform" / "backstage" / "overlays" / "oke"
FOUNDER = ROOT / "backstage" / "founder" / "catalog-info.yaml"


def test_the_proxy_endpoint_targets_the_egress_service_and_reads_auth_from_a_file():
    cfg = yaml.safe_load(CONFIG.read_text())
    ep = cfg["proxy"]["endpoints"]["/sunshine"]
    assert ep["target"].startswith("https://sunshine-mac.backstage.svc")
    assert "POST" in ep["allowedMethods"]
    assert ep["headers"]["Authorization"] == {
        "$file": "/run/secrets/sunshine/AUTHORIZATION"
    }


def test_the_egress_service_carries_the_estate_config_row_not_a_literal_ip():
    docs = list(yaml.safe_load_all((OVERLAY / "sunshine-egress.yaml").read_text()))
    svc = next(d for d in docs if d["kind"] == "Service")
    assert (
        svc["metadata"]["annotations"]["tailscale.com/tailnet-ip"]
        == "${FOUNDER_MAC_TS_IP}"
    )
    assert svc["spec"]["type"] == "ExternalName"
    assert any(p["port"] == 47990 for p in svc["spec"]["ports"])
    es = next(d for d in docs if d["kind"] == "ExternalSecret")
    assert es["spec"]["target"]["name"] == "sunshine-auth"
    assert es["spec"]["secretStoreRef"]["name"] == "estate-vault"


def test_pair_my_phone_is_a_registered_founder_surface():
    docs = [d for d in yaml.safe_load_all(FOUNDER.read_text()) if d]
    ent = next(d for d in docs if d["metadata"]["name"] == "founder-pair-phone")
    assert ent["spec"]["type"] == "founder-surface"
    assert any(l["url"].endswith("/pair") for l in ent["metadata"]["links"])

"""crew#503: the second login hop was real.

Measured 2026-08-29 (session 2d8b3bd0): every founder surface answered 302 to the identity domain
(catalogue, langfuse, signoz, hc), so hop one was green -- and the hourly login drill grades only
the catalogue. Behind the ForwardAuth, Langfuse ran its own email+password sign-in: no AUTH_* env
anywhere in platform/observability, while healthchecks consumed X-Auth-Request-Email as
REMOTE_USER_HEADER. "One login" was two. This file holds the shape that closes it for Langfuse and
names the one surface (SigNoz community edition: Google OAuth only) that cannot be closed by config.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "platform/oci/identity/main.tf"
LANGFUSE = ROOT / "platform/observability/langfuse.yaml"
VALUES = ROOT / "platform/observability/langfuse-values.yaml"
ROUTES = ROOT / "platform/observability/httproute.yaml"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _sso() -> dict:
    es = next(d for d in _docs(LANGFUSE) if d["kind"] == "ExternalSecret" and d["metadata"]["name"] == "langfuse-sso")
    return es["spec"]["target"]["template"]["data"]


def test_identity_domain_holds_a_langfuse_client_whose_callback_is_next_auths() -> None:
    tf = TF.read_text()
    block = re.search(r'resource "oci_identity_domains_app" "langfuse" \{(.*?)\n\}', tf, re.S)
    assert block, "no IDCS app for Langfuse: the second hop is still a password form"
    assert 'redirect_uris             = ["https://langfuse.${var.zone}/api/auth/callback/custom"]' in block.group(1)
    assert 'client_type               = "confidential"' in block.group(1)
    assert 'resource "oci_identity_domains_grant" "langfuse_founder"' in tf, "founder is not granted the app: consent wall"
    for name in ("langfuse-sso-client-id", "langfuse-sso-client-secret"):
        assert f'secret_name    = "{name}"' in tf, f"{name} never reaches the vault"


def test_langfuse_reads_the_client_from_the_vault_and_turns_the_password_form_off() -> None:
    data = _sso()
    assert data["AUTH_CUSTOM_CLIENT_ID"] == "{{ .client_id }}"
    assert data["AUTH_CUSTOM_CLIENT_SECRET"] == "{{ .client_secret }}"
    assert data["AUTH_CUSTOM_ISSUER"] == "${ESTATE_OIDC_DOMAIN_URL}", "discovery lives at the domain URL, not the issuer claim"
    assert data["AUTH_CUSTOM_ID_TOKEN"] == "false", "IDCS issuer claim != discovery host; userinfo path or the sign-in 500s"
    assert data["AUTH_DISABLE_USERNAME_PASSWORD"] == "true", "a password form behind the front door is the second hop"
    assert data["AUTH_CUSTOM_ALLOW_ACCOUNT_LINKING"] == "true", "the LANGFUSE_INIT_ user must merge with the SSO identity"
    es = next(d for d in _docs(LANGFUSE) if d["kind"] == "ExternalSecret" and d["metadata"]["name"] == "langfuse-sso")
    keys = {d["remoteRef"]["key"] for d in es["spec"]["data"]}
    assert keys == {"langfuse-sso-client-id", "langfuse-sso-client-secret"}


def test_the_web_pod_mounts_the_sso_secret() -> None:
    values = yaml.safe_load(VALUES.read_text())
    names = [r["secretRef"]["name"] for r in values["langfuse"]["additionalEnvFrom"]]
    assert "langfuse-sso" in names, "the ExternalSecret exists but no pod reads it"


def test_every_surface_behind_the_front_door_consumes_the_identity_or_is_named() -> None:
    """A ForwardAuth with nothing reading the identity behind it is a second hop. Each such host
    either consumes X-Auth-Request-Email / runs its own OIDC client, or is on the named list with
    the reason a config change cannot close it."""
    cannot_close = {"signoz": "community edition: Google OAuth only, no OIDC and no header auth"}
    consumes = {
        "langfuse": "AUTH_CUSTOM_CLIENT_ID" in _sso(),
        "hc": "REMOTE_USER_HEADER" in (ROOT / "platform/healthchecks/env.yaml").read_text(),
        "catalogue": True,  # Backstage is the portal itself; its identity story is ADR 0003
    }
    hosts = set()
    for path in ROUTES, ROOT / "platform/healthchecks/httproute.yaml", ROOT / "platform/backstage/overlays/oke/httproute.yaml":
        for d in _docs(path):
            if d.get("kind") != "HTTPRoute":
                continue
            for rule in d["spec"]["rules"]:
                if any(f.get("type") == "ExtensionRef" for f in rule.get("filters", [])):
                    hosts.update(h.split(".")[0] for h in d["spec"]["hostnames"])
    assert hosts, "no ForwardAuth route found: the probe is blind"
    open_hops = {h for h in hosts if not consumes.get(h) and h not in cannot_close}
    assert not open_hops, f"second login hop with no reader and no named reason: {sorted(open_hops)}"

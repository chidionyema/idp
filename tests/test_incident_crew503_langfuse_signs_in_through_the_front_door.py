"""crew#503: the second login hop was real.

Measured 2026-08-29 (session 2d8b3bd0): every founder surface answered 302 to the identity domain
(catalogue, langfuse, signoz, hc), so hop one was green -- and the hourly login drill grades only
the catalogue. Behind the ForwardAuth, Langfuse ran its own email+password sign-in: no AUTH_* env
anywhere in platform/observability, while healthchecks consumed X-Auth-Request-Email as
REMOTE_USER_HEADER. "One login" was two. This file holds the shape that closes it for Langfuse and
names the one surface (SigNoz community edition: Google OAuth only) that cannot be closed by config.
"""

from __future__ import annotations

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
    es = next(
        d
        for d in _docs(LANGFUSE)
        if d["kind"] == "ExternalSecret" and d["metadata"]["name"] == "langfuse-sso"
    )
    return es["spec"]["target"]["template"]["data"]


def test_langfuse_reads_the_client_from_the_vault_and_turns_the_password_form_off() -> (
    None
):
    data = _sso()
    assert data["AUTH_CUSTOM_CLIENT_ID"] == "{{ .client_id }}"
    assert data["AUTH_CUSTOM_CLIENT_SECRET"] == "{{ .client_secret }}"
    assert data["AUTH_CUSTOM_ISSUER"] == "${ESTATE_OIDC_DOMAIN_URL}", (
        "discovery lives at the domain URL, not the issuer claim"
    )
    assert data["AUTH_CUSTOM_ID_TOKEN"] == "true", (
        "ID_TOKEN=false fails the callback when the identity domain returns an id_token (vendor page, crew#626)"
    )
    assert data["AUTH_DISABLE_USERNAME_PASSWORD"] == "true", (
        "a password form behind the front door is the second hop"
    )
    assert data["AUTH_CUSTOM_ALLOW_ACCOUNT_LINKING"] == "true", (
        "the LANGFUSE_INIT_ user must merge with the SSO identity"
    )
    es = next(
        d
        for d in _docs(LANGFUSE)
        if d["kind"] == "ExternalSecret" and d["metadata"]["name"] == "langfuse-sso"
    )
    keys = {d["remoteRef"]["key"] for d in es["spec"]["data"]}
    assert keys == {"langfuse-sso-client-id", "langfuse-sso-client-secret"}


def test_next_auths_endpoints_reach_langfuse_without_the_front_door() -> None:
    """A fresh browser lands on /api/auth/callback/custom straight from IDCS; bounced to the front
    door first it loops, and `curl /api/auth/providers` is the proof the founder is shown."""
    api = next(
        d
        for d in _docs(ROUTES)
        if d.get("kind") == "HTTPRoute" and d["metadata"]["name"] == "langfuse-api"
    )
    rule = api["spec"]["rules"][0]
    assert not any(f.get("type") == "ExtensionRef" for f in rule.get("filters", []))
    prefixes = {m["path"]["value"] for m in rule["matches"]}
    assert "/api/auth/" in prefixes, prefixes

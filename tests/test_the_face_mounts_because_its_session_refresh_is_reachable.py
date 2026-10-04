"""The face must MOUNT in a real browser: the app's own auth refresh must reach Backstage.

Measured live 2026-10-04, driving real Chrome at https://catalogue.mumchimp.com/face:
the page booted, called /api/auth/oauth2Proxy/refresh, took the /api/ catch-all's 401
(13 bytes, text/plain), discarded the session and reloaded -- in a loop. guest/refresh
returned 200 throughout. The face itself never loaded: zero canvases, zero requests for
/face/talkinghead.mjs or /face/estate.glb, at every size. The guest carve-out fixed the
door the app was NOT using and left the one it WAS using behind the login it could not pass.

Two facts together caused it, and either alone is a defect, so both are graded here:

  1. The ROUTE -- an auth refresh the SPA calls must not sit behind login-forward-auth. The
     guest rule taught this half; oauth2Proxy was left out.
  2. The CONFIG -- the container build listed a provider whose refresh the edge refuses. A
     provider that cannot complete its refresh is not a fallback, it is a reload loop.

A gate that cannot fail is not a gate: on the tree before this change, fact 2 fails (the
merged config carried both providers) and fact 1 fails (only /api/auth/guest/ was carved).
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE = REPO_ROOT / "platform" / "backstage" / "overlays" / "oke" / "httproute.yaml"
CONTAINER_CONFIG = REPO_ROOT / "backstage" / "app-config.container.yaml"
BASE_CONFIG = REPO_ROOT / "backstage" / "app-config.yaml"

FORWARD_AUTH_PREFIX = "login-forward-auth"

# Every refresh endpoint the SPA may call to establish a session. A session endpoint is
# reachable by definition: gating the door that mints the session is the 2026-10-03 defect
# with a different path.
SESSION_PATHS = ("/api/auth/guest/", "/api/auth/oauth2Proxy/")


def _route_rules() -> list[dict]:
    docs = [d for d in yaml.safe_load_all(ROUTE.read_text()) if isinstance(d, dict)]
    routes = [d for d in docs if d.get("kind") == "HTTPRoute"]
    assert routes, f"no HTTPRoute in {ROUTE.name}"
    return [rule for r in routes for rule in (r.get("spec", {}).get("rules") or [])]


def _prefixes(rule: dict) -> list[str]:
    return [m.get("path", {}).get("value", "") for m in (rule.get("matches") or [])]


def _forward_auth(rule: dict) -> bool:
    names = {
        ((f or {}).get("extensionRef") or {}).get("name", "")
        for f in (rule.get("filters") or [])
    }
    return any(n.startswith(FORWARD_AUTH_PREFIX) for n in names)


def _providers(path: Path) -> dict:
    cfg = yaml.safe_load(path.read_text()) or {}
    return (cfg.get("auth") or {}).get("providers") or {}


def test_every_session_refresh_path_is_reachable_signed_out() -> None:
    """Fact 1: no refresh the SPA calls is gated by the login it is trying to establish."""
    rules = _route_rules()
    for path in SESSION_PATHS:
        matching = [r for r in rules if any(p.startswith(path) for p in _prefixes(r))]
        assert matching, (
            f"no rule in the face route matches {path}. Without an explicit rule the "
            "catch-all gates it and the session can never be minted."
        )
        # The rule that WINS is the most specific; if any matching rule is gated, the path is
        # gated. Assert none of them carry forward-auth.
        gated = [r for r in matching if _forward_auth(r)]
        assert not gated, (
            f"{path} is behind forward-auth in the face route. That is the 2026-10-04 reload "
            "loop: the SPA takes a 401 on its own refresh and reloads forever, so the face "
            "never mounts."
        )


def test_the_data_plane_is_still_gated() -> None:
    """The carve-outs must not have loosened the catch-all that enforces ADR 0003."""
    rules = _route_rules()
    api = [r for r in rules if any(p == "/api/" for p in _prefixes(r))]
    assert api, "no /api/ catch-all -- the data plane has no gate"
    assert all(_forward_auth(r) for r in api), (
        "the /api/ catch-all lost login-forward-auth-api, so every data path is now public. "
        "The fix for the face is a carve-out for its own session endpoints, never a loosening "
        "of /api/catalog/ or /api/proxy/."
    )


def test_the_container_does_not_offer_a_provider_its_edge_refuses() -> None:
    """Fact 2: the deployed build registers only providers whose refresh can succeed.

    app-config.yaml (base) registers oauth2Proxy. The deployed image layers
    app-config.container.yaml on top with a YAML file provider, so the arrays are REPLACED,
    not merged -- the container's `auth.providers` is the whole list at runtime. If the
    container restates a provider the edge 401s, the SPA tries it, fails, and reloads.
    """
    container = _providers(CONTAINER_CONFIG)
    assert container, (
        f"{CONTAINER_CONFIG.name} registers no auth providers. The container build would "
        "inherit the base set, including the oauth2Proxy provider the edge refuses."
    )
    assert "guest" in container, (
        "the container build dropped the guest provider -- on an island, that is no way in."
    )
    refused = {"oauth2Proxy"}
    offered = refused & set(container)
    assert not offered, (
        f"the container build registers {sorted(offered)}, whose /api/auth/oauth2Proxy/refresh "
        "is refused at the edge. A provider that cannot refresh is a reload loop, not a "
        "fallback: measured live, guest/refresh 200 then oauth2Proxy/refresh 401, forever, "
        "with the face never mounting."
    )


def test_the_base_config_still_documents_the_front_door_provider() -> None:
    """The base config is the front door's, and it legitimately keeps oauth2Proxy.

    This pins WHY the container subtracts it: the base is shared with `yarn start` and with
    the OIDC front door, where oauth2Proxy is correct. The subtraction is the container's,
    and only the container's.
    """
    base = _providers(BASE_CONFIG)
    assert "oauth2Proxy" in base, (
        "the base config no longer registers oauth2Proxy. If the front door moved off it, the "
        "container's subtraction is no longer the explanation and this test needs rewriting."
    )

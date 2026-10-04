"""The sign-in page must press a button the deployment actually opens.

The 2026-10-04 defect, measured in a real browser against the live edge: /face never mounted.
The SPA booted, asked /api/auth/oauth2Proxy/refresh, took the edge's 401, threw the session away,
reloaded -- forever. guest/refresh returned 200 the whole time.

The cause was a contradiction in the app, not a missing header. The edge answers
/api/auth/oauth2Proxy/refresh through login-forward-auth-api -> oauth2-proxy's /oauth2/auth, which
returns 401 (or 202 with X-Auth-Request-* headers) only when the browser ALREADY carries the door's
cookie. The face is deliberately reachable WITHOUT that cookie -- its /face and /voice assets are
public and the guest lane exists for a visitor who skipped the door -- so the refresh could never
succeed, and the guest fallthrough inside the error screen reloaded straight back into it.

Two earlier fixes graded the wrong layer and both passed while the face stayed black: one carved
out the guest door (which the app was not calling), the next carved out the oauth2Proxy door
(leaving the app still asking a provider that 500s without the door). This gate grades the ROOT
FACT, the one each of those missed: the sign-in page must name only a provider the deployed edge
serves, and it must not depend on the door for a page that does not require the door.

A gate that cannot fail is not a gate: on the tree before the root fix, the sign-in page read
`provider="oauth2Proxy"` in production, so test_the_signin_page_never_names_a_refused_provider
fails. On the fixed tree it passes, because the page names `guest` alone.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SIGNIN = (
    REPO_ROOT
    / "backstage"
    / "packages"
    / "app"
    / "src"
    / "modules"
    / "signin"
    / "index.tsx"
)
CONTAINER_CONFIG = REPO_ROOT / "backstage" / "app-config.container.yaml"
ROUTE = REPO_ROOT / "platform" / "backstage" / "overlays" / "oke" / "httproute.yaml"

# Providers an unauthenticated browser (the face's only kind of first visitor) can complete.
# guest/refresh is carved at the edge and answers 200 with a real token, no door cookie.
# oauth2Proxy/refresh requires the door's cookie and is gated: it can never complete here.
REQUIRES_DOOR = {"oauth2Proxy"}


def _code_only() -> str:
    """The module's executable lines, comments stripped.

    Several comments name oauth2Proxy precisely to record that it is NOT used, so a provider
    named only in prose must not be counted as behaviour.
    """
    return "\n".join(line.split("//")[0] for line in SIGNIN.read_text().splitlines())


def _providers_named_in_signin() -> set[str]:
    """Every provider literal the module names in code: providers={['guest']} or provider="x"."""
    code = _code_only()
    names: set[str] = set()
    for group in re.findall(r"providers\s*=\s*\{\[([^\]]*)\]\}", code):
        names |= set(re.findall(r"['\"]([A-Za-z0-9_]+)['\"]", group))
    names |= set(re.findall(r"""provider\s*[=:]\s*['\"]([A-Za-z0-9_]+)['\"]""", code))
    return names


def test_the_signin_page_never_names_a_refused_provider() -> None:
    """ROOT FACT: the page presses only buttons this deployment opens."""
    named = _providers_named_in_signin()
    assert named, (
        "the sign-in module names no provider at all -- it cannot sign anyone in. "
        f"read {SIGNIN.relative_to(REPO_ROOT)}"
    )
    refused = named & REQUIRES_DOOR
    assert not refused, (
        f"the sign-in page names {sorted(refused)}, whose refresh the edge refuses without the "
        "door cookie. This is the 2026-10-04 reload loop: the SPA asks, gets 401, reloads, "
        "forever, and the face never mounts. The page must use a provider served without the "
        "door -- guest -- because the face is reached without one."
    )


def test_the_signin_page_does_not_branch_on_node_env() -> None:
    """The provider must not change with the build, or a deployed build can ask one the edge refuses.

    The pre-fix page read `process.env.NODE_ENV !== 'production' ? guest : oauth2Proxy`. That
    branch is what let production pick a provider the edge gates while local/dev picked the one
    that works -- the same code, two behaviours, and only the deployed one was broken.
    """
    code = _code_only()
    assert "NODE_ENV" not in code, (
        "the sign-in page still branches on NODE_ENV. Environment-dependent provider choice is "
        "how production came to ask oauth2Proxy while the face was reached without the door. "
        "One provider, every environment."
    )


def test_the_container_registers_the_provider_the_page_uses() -> None:
    """Config and page must agree: the runtime providers list must contain what the page asks."""
    cfg = yaml.safe_load(CONTAINER_CONFIG.read_text()) or {}
    registered = set(((cfg.get("auth") or {}).get("providers") or {}))
    named = _providers_named_in_signin()
    missing = named - registered
    assert not missing, (
        f"the sign-in page names {sorted(missing)} but the container registers "
        f"{sorted(registered)}. A page asking an unregistered provider is a 500 on the first "
        "refresh -- the SPA then discards the session and reloads."
    )
    assert registered & REQUIRES_DOOR == set(), (
        f"the container registers {sorted(registered & REQUIRES_DOOR)}; the deployed edge gates "
        "that provider's refresh. A provider whose refresh the edge refuses is not a fallback, "
        "it is a reload loop."
    )


def test_the_data_plane_is_still_gated() -> None:
    """The fix must not have loosened the catch-all that enforces ADR 0003."""
    docs = [d for d in yaml.safe_load_all(ROUTE.read_text()) if isinstance(d, dict)]
    rules = [
        rule
        for r in docs
        if r.get("kind") == "HTTPRoute"
        for rule in (r.get("spec", {}).get("rules") or [])
    ]
    api = [
        r
        for r in rules
        if any(
            m.get("path", {}).get("value") == "/api/" for m in (r.get("matches") or [])
        )
    ]
    assert api, "no /api/ catch-all -- the data plane has no gate"
    gated = any(
        any(
            (((f or {}).get("extensionRef") or {}).get("name", "")).startswith(
                "login-forward-auth"
            )
            for f in (r.get("filters") or [])
        )
        for r in api
    )
    assert gated, (
        "the /api/ catch-all lost login-forward-auth-api, so every data path is public. The face "
        "fix is an app-side provider choice; it never loosens /api/catalog/ or /api/proxy/."
    )

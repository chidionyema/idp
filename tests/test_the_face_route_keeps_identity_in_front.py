"""ADR 0003 — identity is OIDC and the gateway enforces it — applied to the face route.

`backstage/app-config.container.yaml` states the rule in its own words, beside the flag it
governs:

    The PR that adds the public route must put identity in front of it in the same change
    (ADR 0003, OIDC at the gateway) or turn this flag off;
    tests/test_incident_backstage_image_critical_cve.py holds that rule.

That cited test no longer exists. The rule has been a comment with nothing behind it since --
and it was already broken once in production: the edge's `/api/` catch-all demanded
`login-forward-auth-api` on `/api/auth/guest/refresh`, so the one door that exists FOR a
signed-out visitor was itself gated. Backstage answered 200 for the guest refresh; the edge
turned it into a 401. The SPA never mounted (0 canvases, 0 requests for /face/* or /voice/*),
and the wall the founder saw was the sign-in screen.

This test is the guard the comment promises. It grades the route the cluster applies, not a
paraphrase of it, and it fails if either half of ADR 0003 is deleted:

  1. the SPA / data catch-all (`/`) still carries the `login-forward-auth` forward-auth filter,
     so nobody enters without the domain (app-config.production.yaml: "No guest provider");
  2. the guest refresh door (`/api/auth/guest/`) does NOT, because a door that requires the
     login it exists to establish can never be walked.

It reads `platform/backstage/overlays/oke/httproute.yaml` -- the manifest `platform/backstage`
applies to the live cluster -- with a YAML parser. A missing file or an unparseable document is
a failure, never a skip: a gate that cannot fail is not a gate.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTE = REPO_ROOT / "platform" / "backstage" / "overlays" / "oke" / "httproute.yaml"

FORWARD_AUTH = "login-forward-auth"


def _rules() -> list[dict]:
    """The HTTPRoute's rules, as the cluster would receive them.

    The manifest is multi-document -- it carries the HTTPRoute and the traefik Middleware
    objects it references -- so the route is selected by kind, not by position.
    """
    assert ROUTE.is_file(), (
        f"the face route is missing: {ROUTE.relative_to(REPO_ROOT)}. "
        "ADR 0003's gate cannot be verified without it."
    )
    docs = [d for d in yaml.safe_load_all(ROUTE.read_text()) if isinstance(d, dict)]
    routes = [d for d in docs if d.get("kind") == "HTTPRoute"]
    assert routes, (
        f"no HTTPRoute document in {ROUTE.name} (found kinds: "
        f"{sorted({d.get('kind') for d in docs})})"
    )
    steps = [r.get("spec", {}).get("rules") for r in routes]
    rules = [rule for rule_set in steps if rule_set for rule in rule_set]
    assert rules, f"{ROUTE.name} carries no rules -- an empty route enforces nothing"
    return rules


def _middleware_names(rule: dict) -> set[str]:
    names = set()
    for f in rule.get("filters") or []:
        ref = (f or {}).get("extensionRef") or {}
        if ref.get("kind") == "Middleware" and ref.get("name"):
            names.add(ref["name"])
    return names


def _matched_prefixes(rule: dict) -> list[str]:
    return [
        m.get("path", {}).get("value", "")
        for m in rule.get("matches") or []
        if isinstance(m, dict)
    ]


def _catch_all_rules(rules: list[dict]) -> list[dict]:
    """Rules with no `matches` at all -- the fall-through, which is `/`."""
    return [r for r in rules if not r.get("matches")]


def test_the_spa_catch_all_puts_identity_in_front() -> None:
    """ADR 0003, half one: the public route carries forward-auth.

    The catch-all is the rule with no `matches`; it decides everything not matched above it,
    which is the SPA document at `/`. If its `login-forward-auth` filter is dropped, the app
    shell is served to the open internet with no identity in front of it -- the change
    app-config.container.yaml forbids ("must put identity in front of it in the same change").
    """
    rules = _rules()
    catch_alls = _catch_all_rules(rules)
    assert catch_alls, (
        "no catch-all rule (one with no `matches`) in the face route: something now decides `/`, "
        "and ADR 0003's gate is not on it. If a rule for `/` was added with its own matches, "
        "this test must be pointed at it -- do not delete the gate."
    )
    gated = [r for r in catch_alls if FORWARD_AUTH in _middleware_names(r)]
    assert gated, (
        f"the catch-all rule does not carry `{FORWARD_AUTH}`. ADR 0003 (identity is OIDC and the "
        "gateway enforces it) and app-config.container.yaml both require identity in front of the "
        "public face route. Middleware on the catch-all: "
        f"{sorted(set().union(*[_middleware_names(r) for r in catch_alls]))}"
    )


def test_the_guest_refresh_door_is_not_gated_by_the_login_it_establishes() -> None:
    """ADR 0003, half two: the door that mints a guest session is reachable signed-out.

    `/api/auth/guest/refresh` exists FOR a visitor who has no session. The `/api/` catch-all
    applies `login-forward-auth-api`; the guest rule must sit above it and must not carry the
    forward-auth filter itself, or the door demands the login it is there to create. This is
    the exact production defect of 2026-10-03 (edge 401 against a Backstage 200), so the test
    names the path and the filter that broke it.
    """
    rules = _rules()
    guest_rules = [
        r
        for r in rules
        if any(p.startswith("/api/auth/guest") for p in _matched_prefixes(r))
    ]
    assert guest_rules, (
        "no rule matches /api/auth/guest/ in the face route. The guest refresh door has been "
        "removed or renamed; a signed-out visitor then has no way in, which is the wall this "
        "rule was added to open (2026-10-03)."
    )
    for r in guest_rules:
        names = _middleware_names(r)
        assert FORWARD_AUTH not in names, (
            "the /api/auth/guest/ rule carries `login-forward-auth`. That is the 2026-10-03 "
            "defect: the edge demanded the login on the one door that exists for a visitor who "
            "has none, Backstage's 200 became the edge's 401, and the SPA never mounted."
        )
        assert not any(n.startswith("login-forward-auth") for n in names), (
            f"the /api/auth/guest/ rule carries a forward-auth middleware: {sorted(names)}"
        )


def test_the_data_plane_keeps_its_gate() -> None:
    """ADR 0003 consequence: opening the shell does not open the data.

    `/api/` (catalogue entities, fleetview proxy) must keep `login-forward-auth-api`. The
    guest-door fix was scoped to `/api/auth/guest/`; if the `/api/` gate was loosened to make
    the wall go away, every data path is now anonymous. The app answering 401 to an
    unauthenticated XHR is the intended shape; the edge answering nothing at all is not.
    """
    rules = _rules()
    api_rules = [
        r for r in rules if any(p.rstrip("/") == "/api" for p in _matched_prefixes(r))
    ]
    assert api_rules, "no rule matches /api -- the data plane has no gate at all"
    gated = [
        r
        for r in api_rules
        if any(n.startswith("login-forward-auth") for n in _middleware_names(r))
    ]
    assert gated, (
        "the /api rule no longer carries `login-forward-auth-api`: the data plane is now "
        "anonymous. Opening the face shell (ADR 0003) does not open catalogue entities or the "
        f"fleetview proxy. Middleware on /api: "
        f"{sorted(set().union(*[_middleware_names(r) for r in api_rules]))}"
    )

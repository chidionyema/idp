"""crew#269 / ADR 0003 + ADR 0007: one hostname per service, one federated login in front of all of them.

Rules (rung 2, properties over every manifest under platform/):
  1. every rule of every HTTPRoute outside the identity namespace carries a ForwardAuth ExtensionRef
     whose Middleware exists in the same namespace and points at oauth2-proxy; the one rule allowed
     without it is the /oauth2/ path that sends the login redirect to oauth2-proxy itself;
  1b. no manifest holds a user database (ADR 0007): no ExternalSecret templates a users file and no
     Middleware names authelia;
  2. no hostname carries a zone literal: it is `<name>.${ESTATE_ZONE:=...}` (LAW 46);
  3. every parentRef sectionName names a listener on the shared Gateway
     (prospector-main/deploy/k8s/base/edge.yaml); BLIND without that checkout, never green.
"""
import glob
import os
import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ESTATE_CODE = pathlib.Path(os.environ.get("ESTATE_CODE", ROOT.parent))
TRAEFIK_HTTPS_PORT = 8443  # the chart's websecure entrypoint; platform/edge/traefik.yaml keeps it
EDGE = ESTATE_CODE / "prospector-main" / "deploy" / "k8s" / "base" / "edge.yaml"


def _docs():
    for f in sorted(glob.glob(str(ROOT / "platform" / "**" / "*.yaml"), recursive=True)):
        for d in yaml.safe_load_all(pathlib.Path(f).read_text()):
            if d:
                yield f, d


ROUTES = [(f, d) for f, d in _docs() if d.get("kind") == "HTTPRoute"]
MIDDLEWARES = {(d["metadata"]["namespace"], d["metadata"]["name"]): d for _, d in _docs() if d.get("kind") == "Middleware"}


def test_routes_exist():
    assert ROUTES, "no HTTPRoute under platform/"


@pytest.mark.parametrize("f,route", ROUTES, ids=[d["metadata"]["name"] for _, d in ROUTES])
def test_every_route_outside_identity_is_behind_forward_auth(f, route):
    ns = route["metadata"]["namespace"]
    if ns == "identity":
        return
    guarded = 0
    for rule in route["spec"]["rules"]:
        refs = [flt["extensionRef"] for flt in rule.get("filters", []) if flt.get("type") == "ExtensionRef"]
        if not refs:
            paths = [m.get("path", {}) for m in rule.get("matches", [])]
            assert paths and all(p == {"type": "PathPrefix", "value": "/oauth2/"} for p in paths), \
                f"{f}: route {route['metadata']['name']} has a rule with no ExtensionRef that is not the /oauth2/ login path"
            assert all(b["name"] == "oauth2-proxy" and b.get("namespace") == "identity" for b in rule["backendRefs"]), \
                f"{f}: the /oauth2/ path must go to identity/oauth2-proxy, nowhere else"
            continue
        guarded += 1
        for ref in refs:
            mw = MIDDLEWARES.get((ns, ref["name"]))
            assert mw, f"{f}: Middleware {ns}/{ref['name']} not found in the route's namespace"
            assert "oauth2-proxy.identity" in mw["spec"]["forwardAuth"]["address"], mw["spec"]
    assert guarded, f"{f}: route {route['metadata']['name']} has no guarded rule"


def test_no_manifest_holds_a_user_database():
    """ADR 0007: the estate holds no password for a person."""
    for f, d in _docs():
        text = yaml.safe_dump(d)
        assert "users_database" not in text and "password_hash" not in text, f"{f}: a user database"
        if d.get("kind") == "Middleware":
            assert "authelia" not in text, f"{f}: Middleware still points at authelia"


@pytest.mark.parametrize("f,route", ROUTES, ids=[d["metadata"]["name"] for _, d in ROUTES])
def test_hostnames_carry_no_zone_literal(f, route):
    for h in route["spec"]["hostnames"]:
        assert re.fullmatch(r"[a-z0-9-]+\.\$\{ESTATE_ZONE\}", h), f"{f}: {h}"


@pytest.mark.parametrize("f,route", ROUTES, ids=[d["metadata"]["name"] for _, d in ROUTES])
def test_every_section_name_is_a_listener_on_the_shared_gateway(f, route):
    if not EDGE.exists():
        pytest.skip(f"BLIND: no prospector-main checkout at {EDGE} (set ESTATE_CODE)")
    gw = next(d for d in yaml.safe_load_all(EDGE.read_text()) if d and d.get("kind") == "Gateway")
    listeners = {l["name"]: l for l in gw["spec"]["listeners"]}
    for p in route["spec"]["parentRefs"]:
        assert p["name"] == gw["metadata"]["name"] and p["namespace"] == gw["metadata"]["namespace"]
        l = listeners.get(p["sectionName"])
        assert l, f"{f}: listener {p['sectionName']} not on {gw['metadata']['name']}"
        assert l["allowedRoutes"]["namespaces"]["from"] == "Selector", f"{p['sectionName']}: routes from other namespaces not allowed"
        host = route["spec"]["hostnames"][0].split(".")[0]
        assert l["hostname"].startswith(host + "."), f"{p['sectionName']} hostname {l['hostname']} != {host}.*"
        # Live 2026-08-26: prospector#734 added these listeners on port 443 and Traefik reported
        # PortUnavailable, because its entrypoints are 8000/8443 on every cluster (idp
        # platform/edge/traefik.yaml) and the overlay patched ports by listener index.
        assert l["port"] == TRAEFIK_HTTPS_PORT, f"{p['sectionName']}: port {l['port']} is no Traefik entrypoint"


def test_the_unguarded_shape_is_refused():
    """A route with no ExtensionRef must fail rule 1 (the guard seen refusing)."""
    bad = {"metadata": {"name": "x", "namespace": "backstage"}, "spec": {"rules": [{"backendRefs": []}]}}
    with pytest.raises(AssertionError):
        test_every_route_outside_identity_is_behind_forward_auth("fixture", bad)
    # an unguarded path that is not the login path, and a login path sent anywhere but oauth2-proxy
    for rule in ({"matches": [{"path": {"type": "PathPrefix", "value": "/api/"}}], "backendRefs": [{"name": "oauth2-proxy", "namespace": "identity"}]},
                 {"matches": [{"path": {"type": "PathPrefix", "value": "/oauth2/"}}], "backendRefs": [{"name": "catalogue"}]}):
        with pytest.raises(AssertionError):
            test_every_route_outside_identity_is_behind_forward_auth("fixture", {"metadata": bad["metadata"], "spec": {"rules": [rule]}})

"""crew#269 / ADR 0003: one hostname per service, one login in front of all of them.

Rules (rung 2, properties over every manifest under platform/):
  1. every HTTPRoute outside the identity namespace carries a ForwardAuth ExtensionRef whose
     Middleware exists in the same namespace and points at Authelia;
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
    refs = [flt["extensionRef"] for rule in route["spec"]["rules"] for flt in rule.get("filters", [])
            if flt.get("type") == "ExtensionRef"]
    assert refs, f"{f}: route {route['metadata']['name']} has no ExtensionRef filter"
    for ref in refs:
        mw = MIDDLEWARES.get((ns, ref["name"]))
        assert mw, f"{f}: Middleware {ns}/{ref['name']} not found in the route's namespace"
        assert "authelia" in mw["spec"]["forwardAuth"]["address"], mw["spec"]


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


def test_the_unguarded_shape_is_refused():
    """A route with no ExtensionRef must fail rule 1 (the guard seen refusing)."""
    bad = {"metadata": {"name": "x", "namespace": "backstage"}, "spec": {"rules": [{"backendRefs": []}]}}
    with pytest.raises(AssertionError):
        test_every_route_outside_identity_is_behind_forward_auth("fixture", bad)

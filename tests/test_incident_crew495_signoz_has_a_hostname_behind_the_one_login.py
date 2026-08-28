"""crew#495 CP8: SigNoz, the telemetry backend, had no hostname, so nobody could open it and no
Terraform run had an endpoint for alert rules. The route is the same shape as langfuse: the login
callback goes to oauth2-proxy, everything else passes login-forward-auth to the chart's `signoz`
service on 8080. Incident test: one route, both rules, on its own edge listener."""

from pathlib import Path

import yaml

ROUTE = Path(__file__).resolve().parents[1] / "platform" / "observability" / "httproute.yaml"


def _route(name: str) -> dict:
    docs = [d for d in yaml.safe_load_all(ROUTE.read_text()) if d]
    routes = [d for d in docs if d["kind"] == "HTTPRoute" and d["metadata"]["name"] == name]
    assert len(routes) == 1, [d["metadata"]["name"] for d in docs]
    return routes[0]


def test_signoz_route_is_on_its_own_listener_behind_the_one_login() -> None:
    route = _route("signoz")
    assert route["spec"]["parentRefs"][0]["sectionName"] == "https-signoz"
    assert route["spec"]["hostnames"] == ["signoz.${ESTATE_ZONE}"]
    oauth, app = route["spec"]["rules"]
    assert oauth["matches"][0]["path"]["value"] == "/oauth2/"
    assert oauth["backendRefs"][0]["name"] == "oauth2-proxy"
    assert app["filters"][0]["extensionRef"]["name"] == "login-forward-auth"
    assert app["backendRefs"] == [{"name": "signoz", "port": 8080}]


def test_langfuse_and_signoz_do_not_share_a_listener() -> None:
    """A second route on https-langfuse would be served for the wrong hostname."""
    assert _route("langfuse")["spec"]["parentRefs"][0]["sectionName"] != _route("signoz")["spec"]["parentRefs"][0]["sectionName"]

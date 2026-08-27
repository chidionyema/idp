"""Binds features/gates/front-door-login.feature (ADR 0007, crew#269, crew#297). The step parses every
YAML document under platform/ for real: no user database, no Authelia, oauth2-proxy in front of every route."""
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then

scenarios("features/gates/front-door-login.feature")

IDP = Path(__file__).resolve().parents[3]
PLATFORM = IDP / "platform"



def api_key_enforced(cfg: str) -> bool:
    """True when an agentgateway config carries a strict apiKey policy with a hashed key: the
    two-part proof an `idp.estate/auth: api-key` route must show (crew#458)."""
    return "apiKey:" in cfg and "mode: strict" in cfg and "keyHash: sha256:" in cfg

def _docs() -> list[tuple[Path, dict]]:
    out = []
    for p in sorted(PLATFORM.rglob("*.y*ml")):
        try:
            docs = list(yaml.safe_load_all(p.read_text()))
        except yaml.YAMLError:
            continue  # templates Flux substitutes; nothing here is a Middleware or ExternalSecret
        out.extend((p, d) for d in docs if isinstance(d, dict) and "kind" in d)
    return out


@pytest.fixture
def state() -> dict:
    return {}


@given("every file under platform/")
def _platform(state: dict) -> None:
    state["docs"] = _docs()
    assert state["docs"], "platform/ holds no Kubernetes manifest"


@then("no ExternalSecret renders a users file and no ForwardAuth points at authelia")
def _no_user_db(state: dict) -> None:
    for p, d in state["docs"]:
        if d["kind"] == "ExternalSecret":
            keys = [str(x.get("secretKey", "")) + str(x.get("remoteRef", {}).get("property", "")) for x in d.get("spec", {}).get("data", [])]
            keys += list((d.get("spec", {}).get("target", {}).get("template", {}).get("data") or {}).keys())
            # crew#516 CP5: the one `users` key allowed is the htpasswd line a basicAuth Middleware in
            # the same file reads for a route annotated edge-basic-auth (one program credential,
            # written by platform/oci/otlp-ingest.tf, not a person's password).
            readers = {str(m.get("spec", {}).get("basicAuth", {}).get("secret", ""))
                       for pp, m in state["docs"] if pp == p and m["kind"] == "Middleware"}
            if d["metadata"]["name"] not in readers:
                assert not any("users" in k.lower() for k in keys), f"{p}: {d['metadata']['name']} renders a users file"
        if d["kind"] == "Middleware":
            addr = str(d.get("spec", {}).get("forwardAuth", {}).get("address", ""))
            assert "authelia" not in addr, f"{p}: {d['metadata']['name']} forwards auth to authelia"


@then("every route outside identity is behind oauth2-proxy, or is a machine API whose own config proves a bearer master key")
def _oauth2_proxy_in_front(state: dict) -> None:
    middlewares = {d["metadata"]["name"]: str(d.get("spec", {}).get("forwardAuth", {}).get("address", ""))
                   for _, d in state["docs"] if d["kind"] == "Middleware"}
    routes = [(p, d) for p, d in state["docs"] if d["kind"] == "HTTPRoute" and p.relative_to(PLATFORM).parts[0] != "identity"]
    assert routes, "no HTTPRoute outside platform/identity"
    for p, d in routes:
        refs = [f.get("extensionRef", {}).get("name") for r in d.get("spec", {}).get("rules", []) for f in r.get("filters", [])]
        if any("oauth2-proxy" in middlewares.get(n, "") for n in refs):
            continue
        # A machine API (the model router, crew#284) cannot sit behind a browser login. It may skip
        # oauth2-proxy only when it says so on the route AND its own config shows the key is enforced;
        # the annotation alone is a label, and a label is not a proof.
        auth = (d["metadata"].get("annotations") or {}).get("idp.estate/auth")
        if auth == "langfuse-project-keys":
            # The trace store's public API (crew#325): Langfuse enforces the project keys on
            # /api/public/, so the route may expose that path and nothing else.
            paths = [m.get("path", {}) for r in d["spec"]["rules"] for m in r.get("matches", [])]
            assert paths and all(x == {"type": "PathPrefix", "value": "/api/public/"} for x in paths), f"{p}: langfuse-project-keys route exposes {paths}"
            keys = (p.parent / "langfuse.yaml").read_text()
            assert "langfuse-init-public-key" in keys and "langfuse-init-secret-key" in keys, f"{p}: langfuse.yaml pulls no project keys"
            continue
        if auth == "api-key":
            # The MCP gateway (crew#458): agentgateway enforces the key itself, and the proof is a
            # strict apiKey policy with a hashed key in the config that sits beside the route.
            gw = p.parent / "agentgateway.yaml"
            assert gw.exists() and api_key_enforced(gw.read_text()), f"{p}: annotated api-key but {gw} enforces no strict apiKey"
            continue
        if auth == "healthchecks-ping-key":
            # The job monitor's ping path (crew#177): the jobs' curl carries the project ping key
            # in the URL, so the route may expose /ping/ and nothing else, and the row must pull
            # that key from the vault and pin it on the project.
            paths = [m.get("path", {}) for r in d["spec"]["rules"] for m in r.get("matches", [])]
            assert paths and all(x == {"type": "PathPrefix", "value": "/ping/"} for x in paths), f"{p}: healthchecks-ping-key route exposes {paths}"
            assert "healthchecks-ping-key" in (p.parent / "external-secret.yaml").read_text(), f"{p}: the row pulls no ping key"
            assert 'project.ping_key = os.environ["PING_KEY"]' in (p.parent / "healthchecks.yaml").read_text(), f"{p}: the row never pins the ping key"
            continue
        if auth == "edge-basic-auth":
            # The collector's ingest door (crew#516 CP5): OTLP /v1/ paths only, and every rule carries a
            # basicAuth Middleware whose Secret an ExternalSecret in the same file pulls from the vault.
            paths = [m.get("path", {}) for r in d["spec"]["rules"] for m in r.get("matches", [])]
            assert paths and all(x.get("type") == "PathPrefix" and x.get("value") in ("/v1/logs", "/v1/traces", "/v1/metrics") for x in paths), f"{p}: edge-basic-auth route exposes {paths}"
            basic = {m["metadata"]["name"]: str(m.get("spec", {}).get("basicAuth", {}).get("secret", ""))
                     for pp, m in state["docs"] if pp == p and m["kind"] == "Middleware" and m.get("spec", {}).get("basicAuth")}
            pulled = {m["metadata"]["name"] for pp, m in state["docs"] if pp == p and m["kind"] == "ExternalSecret"}
            for r in d["spec"]["rules"]:
                names = [f.get("extensionRef", {}).get("name") for f in r.get("filters", [])]
                assert any(n in basic for n in names), f"{p}: a rule of {d['metadata']['name']} carries no basicAuth Middleware ({names})"
                assert all(basic[n] in pulled for n in names if n in basic), f"{p}: the basicAuth Secret is pulled by no ExternalSecret in the file"
            continue
        assert auth == "bearer-master-key", f"{p}: route {d['metadata']['name']} has no oauth2-proxy Middleware in front ({refs}) and no idp.estate/auth annotation"
        cfg = p.parent / "config.yaml"
        assert cfg.exists() and "master_key: os.environ/" in cfg.read_text(), f"{p}: annotated bearer-master-key but {cfg} enforces no master_key"

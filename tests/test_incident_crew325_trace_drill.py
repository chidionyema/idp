"""Incident crew#325, 2026-08-26: the showcase's last step, one routed call visible as a trace at
langfuse.<zone>, had no command that proved it, and the login ForwardAuth in front of every
Langfuse path meant no program could have read a trace back anyway. The rule: the trace drill
exists as a catalogued drill, and Langfuse's key-authenticated public API bypasses the login."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _route(name: str, ns_file: Path) -> dict:
    docs = [d for d in yaml.safe_load_all(ns_file.read_text()) if d]
    return next(d for d in docs if d["kind"] == "HTTPRoute" and d["metadata"]["name"] == name)


def test_langfuse_public_api_bypasses_the_login_forward_auth() -> None:
    route = _route("langfuse", ROOT / "platform" / "observability" / "httproute.yaml")
    public = [
        r for r in route["spec"]["rules"]
        if any(m.get("path", {}).get("value") == "/api/public/" for m in r.get("matches", []))
    ]
    assert public, "no rule for /api/public/ on the langfuse route"
    assert not public[0].get("filters"), "the public API rule must carry no ForwardAuth filter"
    assert public[0]["backendRefs"][0]["name"] == "langfuse-web"
    # Every other non-/oauth2/ rule still goes through the login.
    for r in route["spec"]["rules"]:
        paths = {m.get("path", {}).get("value") for m in r.get("matches", [])}
        if paths & {"/oauth2/", "/api/public/"}:
            continue
        assert any(f.get("extensionRef", {}).get("name") == "login-forward-auth" for f in r.get("filters", [])), r


def test_trace_drill_is_catalogued_and_reads_keys_only_from_the_vault() -> None:
    drills = {d["name"]: d for d in yaml.safe_load((ROOT / "drills" / "catalogue.yaml").read_text())["drills"]}
    assert "trace-drill" in drills
    assert (ROOT / ".github" / "workflows" / drills["trace-drill"]["workflow"]).exists()
    script = (ROOT / "bin" / "idp-trace-drill").read_text()
    # The three secrets are named, never typed (LAW 46): a key literal would look like sk-... or pk-lf-...
    for name in ("litellm-upstream", "langfuse-init-public-key", "langfuse-init-secret-key"):
        assert name in script, name
    assert not re.search(r"(sk-lf-|pk-lf-|sk-)[A-Za-z0-9]{8,}", script), "a key literal in the drill"

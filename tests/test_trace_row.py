"""crew#325 showcase: one call through the router is one trace in Langfuse, opened behind the one login.
Rules (rung 2, properties over the manifests; rung 4 for the suspend incident):
  1. the router reports every call to Langfuse: litellm_settings.success_callback and failure_callback
     name `langfuse`, the env the callback reads (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY) is templated
     by an ExternalSecret in the llm namespace from the same vault entries Langfuse is initialised with,
     and LANGFUSE_HOST names the Langfuse web Service;
  2. the Langfuse keys are optional to the pod: the router starts without them (LAW 38);
  3. the observability row is not suspended (the 2 OCPU node it was suspended for was replaced on
     2026-08-26, crew#289) and substitutes ESTATE_ZONE because it now publishes a hostname;
  4. the observability namespace carries the edge-attach label the shared Gateway selects on, and the
     identity ReferenceGrant lets its route reach oauth2-proxy (the front-door property in
     test_front_door_every_route_is_behind_the_one_login.py covers the route itself).
"""
import pathlib
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _docs(rel):
    return [d for d in yaml.safe_load_all((ROOT / rel).read_text()) if d]


def _one(rel, kind, name):
    hits = [d for d in _docs(rel) if d.get("kind") == kind and d["metadata"]["name"] == name]
    assert len(hits) == 1, (rel, kind, name, len(hits))
    return hits[0]


def test_router_reports_every_call_to_langfuse():
    cfg = yaml.safe_load((ROOT / "platform/llm/config.yaml").read_text())
    s = cfg["litellm_settings"]
    assert "langfuse" in s.get("success_callback", []) and "langfuse" in s.get("failure_callback", [])
    es = _one("platform/llm/external-secret.yaml", "ExternalSecret", "litellm-langfuse")
    data = es["spec"]["target"]["template"]["data"]
    assert set(data) == {"LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"}
    remote = {d["remoteRef"]["key"] for d in es["spec"]["data"]}
    init = _one("platform/observability/langfuse.yaml", "ExternalSecret", "langfuse-init")
    init_remote = {d["remoteRef"]["key"] for d in init["spec"]["data"]}
    assert remote <= init_remote, "the router must read the keys Langfuse was initialised with, not a second pair"
    dep = _one("platform/llm/litellm.yaml", "Deployment", "litellm")
    c = dep["spec"]["template"]["spec"]["containers"][0]
    env = {e["name"]: e.get("value") for e in c["env"]}
    assert env["LANGFUSE_HOST"] == "http://langfuse-web.observability.svc:3000"
    # idp#253: the cluster policy no-optional-secret-references refused `optional: true` (crew#284), so
    # the keys arrive as a mounted, required volume; the vault holds them (langfuse-init above).
    vols = {v["name"]: v for v in dep["spec"]["template"]["spec"]["volumes"]}
    assert vols["langfuse"]["secret"]["secretName"] == "litellm-langfuse"
    assert not vols["langfuse"]["secret"].get("optional", False)
    assert "envFrom" not in c


def test_incident_crew325_observability_row_runs_on_the_replaced_node():
    ks = _one("clusters/oke/platform.yaml", "Kustomization", "observability")
    assert ks["spec"].get("suspend", False) is False
    subs = {s["name"] for s in ks["spec"]["postBuild"]["substituteFrom"]}
    assert "estate-config" in subs


def test_observability_route_can_reach_the_front_door():
    ns = _one("platform/observability/namespace.yaml", "Namespace", "observability")
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"
    grant = _one("platform/identity/httproute.yaml", "ReferenceGrant", "front-door-oauth2-path")
    assert {f["namespace"] for f in grant["spec"]["from"]} >= {"backstage", "observability"}
    route = _one("platform/observability/httproute.yaml", "HTTPRoute", "langfuse")
    assert route["spec"]["parentRefs"][0]["sectionName"] == "https-langfuse"
    assert route["spec"]["hostnames"] == ["langfuse.${ESTATE_ZONE}"]

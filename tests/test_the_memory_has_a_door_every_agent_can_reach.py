"""The unified memory server has a door an agent outside the cluster can reach.

Measured 2026-09-27: the server was merged (#4557) and deployed, and its Deployment had never
left 0/0. Its only door was the in-cluster Host unified-memory.estate.internal, so no laptop
agent, phone or remote session could reach it, and nothing ever woke it. Each assertion below is
one hop of the path mcp.${ESTATE_ZONE}/memories -> traefik (edge) -> KEDA interceptor (keda) ->
server (unified-memory); drop any one and the request dies on that hop.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
MEM = REPO / "platform" / "unified-memory-server"


def docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def one(path: Path, kind: str, name: str | None = None) -> dict:
    (d,) = [
        d
        for d in docs(path)
        if d["kind"] == kind and (name is None or d["metadata"]["name"] == name)
    ]
    return d


def test_the_door_routes_memory_paths_on_the_mcp_host_to_the_interceptor():
    route = one(MEM / "door.yaml", "HTTPRoute")
    assert route["metadata"]["namespace"] == "unified-memory"
    assert route["spec"]["hostnames"] == ["mcp.${ESTATE_ZONE}"]
    (parent,) = route["spec"]["parentRefs"]
    assert parent == {
        "name": "prospector-edge",
        "namespace": "prospector",
        "sectionName": "https-mcp",
    }
    (rule,) = route["spec"]["rules"]
    prefixes = {m["path"]["value"] for m in rule["matches"]}
    assert prefixes == {"/memories", "/digest"}
    (backend,) = rule["backendRefs"]
    # The chart's real Service name, read live from the keda namespace.
    assert backend == {
        "name": "keda-add-ons-http-interceptor-proxy",
        "namespace": "keda",
        "port": 8080,
    }
    for f in rule.get("filters", []):
        name = f["extensionRef"]["name"]
        one(MEM / "door.yaml", "Middleware", name)  # lives in the route's namespace


def test_the_door_is_in_the_kustomization_and_the_row_substitutes_the_zone():
    kz = yaml.safe_load((MEM / "kustomization.yaml").read_text())
    assert "door.yaml" in kz["resources"]
    row = yaml.safe_load(
        (REPO / "clusters" / "oke" / "unified-memory.yaml").read_text()
    )
    assert {"kind": "ConfigMap", "name": "estate-config"} in row["spec"]["postBuild"][
        "substituteFrom"
    ]
    # '$run' in the ImagePolicy must survive the row's substitution.
    policy = one(MEM / "image.yaml", "ImagePolicy")
    assert (
        policy["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/substitute"]
        == "disabled"
    )


def test_the_interceptor_knows_the_door_host_and_the_gateway_may_attach():
    manifest = MEM / "oke-unified-memory.yaml"
    hso = one(manifest, "HTTPScaledObject")
    assert "mcp.${ESTATE_ZONE}" in hso["spec"]["hosts"]
    ns = one(manifest, "Namespace")
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"


def test_the_grant_lets_the_door_reach_the_real_proxy_service():
    grant = one(REPO / "platform" / "keda" / "referencegrant.yaml", "ReferenceGrant")
    assert {
        "group": "gateway.networking.k8s.io",
        "kind": "HTTPRoute",
        "namespace": "unified-memory",
    } in grant["spec"]["from"]
    assert {
        "group": "",
        "kind": "Service",
        "name": "keda-add-ons-http-interceptor-proxy",
    } in grant["spec"]["to"]


def test_the_fence_is_open_both_ways_between_edge_and_keda():
    allow = yaml.safe_load(
        (REPO / "platform" / "ns-fences" / "allowances.yaml").read_text()
    )
    spaces = allow["flows"]
    assert "edge" in spaces["keda"]["ingress_from"]
    assert "keda" in spaces["edge"]["egress"]
    for ns, other in (("edge", "keda"), ("keda", "edge")):
        rendered = (
            REPO / "platform" / "ns-fences" / "network" / f"{ns}.yaml"
        ).read_text()
        assert other in rendered

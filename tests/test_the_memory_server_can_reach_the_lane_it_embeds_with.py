"""The memory server's embed lane is a hop across a fence, so the fence has to say so.

The memory server embeds every fact it stores and every recall query by calling the router's
`embed` lane (MEMORY_EMBED_URL, litellm.llm.svc). allowances.yaml still said "it calls no model",
so llm's default-deny dropped every one of those calls. Nothing raised: the embed helper returns
None on a timeout by design, the fact is stored without a vector, and the router's log never sees
the request. Measured 2026-10-13 after the backfill shipped: /embeddings/backfill failed 2 of 2
per call on the 20s timeout, 47 facts stayed unvectorised, and recall by meaning had nothing to
search. This reads the namespace off the URL the deployment actually holds, so moving the lane
moves the declaration it demands.
"""

import pathlib
import urllib.parse

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ALLOWANCES = ROOT / "platform" / "ns-fences" / "allowances.yaml"
DEPLOY = ROOT / "platform" / "unified-memory-server" / "oke-unified-memory.yaml"
HERE = "unified-memory"


def _embed_namespace() -> str:
    for doc in yaml.safe_load_all(DEPLOY.read_text()):
        if not doc or doc.get("kind") != "Deployment":
            continue
        for container in doc["spec"]["template"]["spec"]["containers"]:
            for env in container.get("env") or []:
                if env["name"] == "MEMORY_EMBED_URL":
                    # <service>.<namespace>.svc[.cluster.local]
                    return urllib.parse.urlsplit(env["value"]).hostname.split(".")[1]
    raise AssertionError("the memory server's Deployment holds no MEMORY_EMBED_URL")


def test_the_memory_server_declares_egress_to_its_embed_lane():
    flows = yaml.safe_load(ALLOWANCES.read_text())["flows"]
    assert _embed_namespace() in (flows[HERE].get("egress") or [])


def test_the_embed_lane_admits_the_memory_server():
    flows = yaml.safe_load(ALLOWANCES.read_text())["flows"]
    assert HERE in (flows[_embed_namespace()].get("ingress_from") or [])


def test_the_rendered_fence_admits_the_memory_server():
    ns = _embed_namespace()
    docs = yaml.safe_load_all(
        (ROOT / "platform" / "ns-fences" / "network" / f"{ns}.yaml").read_text()
    )
    ingress = next(
        d for d in docs if d and d["metadata"]["name"] == "allow-declared-ingress"
    )
    admitted = {
        peer["namespaceSelector"]["matchLabels"]["kubernetes.io/metadata.name"]
        for rule in ingress["spec"]["ingress"]
        for peer in rule["from"]
        if "namespaceSelector" in peer
    }
    assert HERE in admitted

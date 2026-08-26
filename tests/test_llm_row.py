"""The `llm` Flux row (crew#284 CP2, crew#313): LiteLLM as an estate service on OKE.

Rung 2 (property over the two config files) and rung 4 (incident crew#313: the router ran only
on the founder's Mac, so stopping colima took every routed model call down). The rule under
test: the cluster router is the laptop router minus the entries the cluster cannot reach.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CLUSTER = ROOT / "platform" / "llm"
LAPTOP_CFG = yaml.safe_load((ROOT / "llm" / "config.yaml").read_text())
CLUSTER_CFG = yaml.safe_load((CLUSTER / "config.yaml").read_text())


def _models(cfg: dict) -> dict[str, dict]:
    return {m["model_name"]: m["litellm_params"] for m in cfg["model_list"]}


def test_cluster_router_is_laptop_router_minus_local_lane() -> None:
    laptop, cluster = _models(LAPTOP_CFG), _models(CLUSTER_CFG)
    local = {n for n, p in laptop.items() if "host.docker.internal" in str(p.get("api_base", ""))}
    assert local, "the laptop config is expected to carry the ollama lane"
    hosted = {n: p for n, p in laptop.items() if n not in local}
    assert {n: cluster[n] for n in hosted} == hosted, "hosted entries drifted between the two files"
    assert not [n for n, p in cluster.items() if "host.docker.internal" in str(p.get("api_base", ""))]
    # Every fallback target on the cluster must be a cluster model.
    for entry in CLUSTER_CFG["router_settings"]["fallbacks"]:
        for src, targets in entry.items():
            assert src in cluster and set(targets) <= set(cluster), (src, targets)


def test_vision_alias_names_a_capability() -> None:
    cluster = _models(CLUSTER_CFG)
    assert cluster["vision"]["model"] == cluster["gemini"]["model"]


def test_image_version_matches_laptop_compose() -> None:
    laptop = re.search(r"image:\s*ghcr\.io/berriai/litellm-database:(\S+)", (ROOT / "llm" / "litellm.yml").read_text())
    cluster = re.search(r"image:\s*ghcr\.io/berriai/litellm:(\S+)", (CLUSTER / "litellm.yaml").read_text())
    assert laptop and cluster and laptop.group(1) == cluster.group(1)


def test_secret_env_names_cover_every_os_environ_ref() -> None:
    refs = set(re.findall(r"os\.environ/([A-Z_]+)", (CLUSTER / "config.yaml").read_text()))
    documented = set(re.findall(r"([A-Z_]+_KEY)=\1", (CLUSTER / "external-secret.yaml").read_text()))
    assert refs == documented, (refs ^ documented)
    # The file holds two ExternalSecrets since the Langfuse callback (crew#325); this rule is about the upstream one.
    es = next(d for d in yaml.safe_load_all((CLUSTER / "external-secret.yaml").read_text()) if d["metadata"]["name"] == "litellm-upstream")
    assert es["spec"]["dataFrom"][0]["extract"]["key"] == "litellm-upstream"
    dep = next(d for d in yaml.safe_load_all((CLUSTER / "litellm.yaml").read_text()) if d["kind"] == "Deployment")
    assert dep["spec"]["template"]["spec"]["containers"][0]["envFrom"][0]["secretRef"]["name"] == es["spec"]["target"]["name"]


def test_route_attaches_to_the_edge_llm_listener() -> None:
    route = yaml.safe_load((CLUSTER / "httproute.yaml").read_text())
    assert route["spec"]["parentRefs"][0] == {"name": "prospector-edge", "namespace": "prospector", "sectionName": "https-llm"}
    assert route["spec"]["hostnames"] == ["llm.${ESTATE_ZONE}"]
    ns = yaml.safe_load((CLUSTER / "namespace.yaml").read_text())
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"


def test_flux_row_waits_on_edge_and_secret_store() -> None:
    rows = [d for d in yaml.safe_load_all((ROOT / "clusters" / "oke" / "platform.yaml").read_text()) if d]
    llm = next(d for d in rows if d["metadata"]["name"] == "llm")
    assert llm["spec"]["path"] == "./platform/llm"
    assert {d["name"] for d in llm["spec"]["dependsOn"]} >= {"edge", "secret-store"}
    assert llm["spec"]["wait"] is True
    assert llm["spec"]["postBuild"]["substituteFrom"][0]["name"] == "estate-config"

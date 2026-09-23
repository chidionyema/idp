"""hermes-v2, the product, rides the platform's Flux road as the `hermes-agent` row.

The five-day audit (crew, docs/audits/2026-09-03-five-day-capability-audit.md, section 5) named
"onboard hermes-v2 onto the Flux road" as open work. Measured 2026-09-03 it was not open:
hermes-v2's own Dockerfile and build-agent-image.yml push ghcr.io/chidionyema/hermes-agent; this
repository's `hermes-agent` row runs that image on OKE (Flux Ready at main, pod 2/2 Running); the
catalogue holds it as a platform layer, a founder card and the Hermes company domain; its model
traces leave through the router and the Langfuse keys the vault projects. No launchd job named
architect or hermes exists on the founder's Mac any more (launchctl list, 2026-09-03).

What was missing was the rule that says so, so the next audit or session does not "onboard" it a
second time. A second Deployment of one Telegram poller on one token is 409s on both
(platform/hermes-agent/gateway.yaml header, crew#284). Rung 2, properties over the tree, proved
both ways with mutated copies.
"""
# ruff: noqa: S101

from __future__ import annotations

import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROW_DIR = ROOT / "platform" / "hermes-agent"
IMAGE = "ghcr.io/chidionyema/hermes-agent"
PRODUCT_REPO = "https://github.com/chidionyema/hermes-v2"


def _docs(path: Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def flux_rows() -> list[dict]:
    rows = []
    for f in sorted((ROOT / "clusters" / "oke").glob("*.yaml")):
        rows += [
            d
            for d in _docs(f)
            if d.get("kind") == "Kustomization" and "fluxcd" in d.get("apiVersion", "")
        ]
    return rows


# --- properties ---------------------------------------------------------------------------------


def exactly_one_row_carries_the_product(rows: list[dict]) -> bool:
    """One row and one only points at platform/hermes-agent, and nothing is named hermes-v2."""
    at_dir = [r for r in rows if r["spec"].get("path") == "./platform/hermes-agent"]
    named_v2 = [
        r
        for r in rows
        if r["metadata"]["name"] == "hermes-v2"
        or r["spec"].get("path") == "./platform/hermes-v2"
    ]
    return (
        len(at_dir) == 1
        and at_dir[0]["metadata"]["name"] == "hermes-agent"
        and not named_v2
    )


def the_row_is_a_real_road(row: dict) -> bool:
    spec = row["spec"]
    deps = {d["name"] for d in spec.get("dependsOn", [])}
    checks = {
        (h["kind"], h["name"], h["namespace"]) for h in spec.get("healthChecks", [])
    }
    return (
        spec.get("prune") is True
        and spec.get("wait") is True
        and "secret-store" in deps
        and ("Deployment", "hermes-agent-gateway", "hermes-agent") in checks
    )


def the_image_is_the_products_build(
    gateway_docs: list[dict], kust: dict, kust_text: str, automation: list[dict]
) -> bool:
    """The pod runs the image hermes-v2 builds, and Flux moves its tag from that build."""
    (dep,) = [d for d in gateway_docs if d["kind"] == "Deployment"]
    (gw,) = [
        c
        for c in dep["spec"]["template"]["spec"]["containers"]
        if c["name"] == "gateway"
    ]
    pinned = [i for i in kust.get("images", []) if i.get("name") == IMAGE]
    policy = [
        d
        for d in automation
        if d["kind"] == "ImagePolicy" and d["metadata"]["name"] == "hermes-agent"
    ]
    repo = [
        d
        for d in automation
        if d["kind"] == "ImageRepository" and d["spec"].get("image") == IMAGE
    ]
    return (
        gw["image"] == IMAGE
        and len(pinned) == 1
        and '"$imagepolicy": "flux-system:hermes-agent:tag"' in kust_text
        and len(policy) == 1
        and len(repo) == 1
    )


def the_catalogue_holds_it(
    platform_entities: list[dict], founder_entities: list[dict], gen_text: str
) -> bool:
    layer = [
        e
        for e in platform_entities
        if e["kind"] == "Component" and e["metadata"]["name"] == "layer-hermes-agent"
    ]
    otto = [
        e
        for e in founder_entities
        if e["kind"] == "Component" and e["metadata"]["name"] == "founder-otto"
    ]
    company = [
        e
        for e in founder_entities
        if e["kind"] == "Component" and e["metadata"]["name"] == "company-hermes"
    ]
    if not (len(layer) == 1 and len(otto) == 1 and len(company) == 1):
        return False
    la = layer[0]["metadata"]["annotations"]
    oa = otto[0]["metadata"]["annotations"]
    company_links = [link["url"] for link in company[0]["metadata"].get("links", [])]
    return (
        la.get("estate/flux-kustomization") == "hermes-agent"
        and la.get("estate/path") == "./platform/hermes-agent"
        and oa.get("backstage.io/kubernetes-id") == "hermes-agent-gateway"
        and oa.get("backstage.io/kubernetes-namespace") == "hermes-agent"
        and any(u.endswith("/domain/hermes-v2") for u in company_links)
        and '"hermes-v2":' in gen_text
        and PRODUCT_REPO in gen_text
    )


def its_traces_reach_the_estate(
    gateway_docs: list[dict], langfuse_docs: list[dict]
) -> bool:
    """Model traces: the router carries them (STANDARDS observability row); the agent's own go to
    the in-cluster Langfuse with keys the vault projects, never a literal."""
    (dep,) = [d for d in gateway_docs if d["kind"] == "Deployment"]
    pod = dep["spec"]["template"]["spec"]
    (gw,) = [c for c in pod["containers"] if c["name"] == "gateway"]
    env = {e["name"]: e.get("value") for e in gw["env"]}
    projected = {
        s["secret"]["name"]
        for v in pod["volumes"]
        for s in v.get("projected", {}).get("sources", [])
        if "secret" in s
    }
    es = [
        d
        for d in langfuse_docs
        if d["kind"] == "ExternalSecret"
        and d["metadata"]["name"] == "hermes-agent-langfuse"
    ]
    keys = {d["secretKey"] for e in es for d in e["spec"]["data"]}
    return (
        str(env.get("LANGFUSE_BASE_URL", "")).startswith(
            "http://langfuse-web.observability.svc"
        )
        and "hermes-agent-langfuse" in projected
        and {"LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"} <= keys
        and not any(k.startswith("LANGFUSE_") and k.endswith("_KEY") for k in env)
    )


# --- the tree as committed ----------------------------------------------------------------------


def _row() -> dict:
    (row,) = [r for r in flux_rows() if r["metadata"]["name"] == "hermes-agent"]
    return row


def test_exactly_one_flux_row_carries_hermes_v2_and_no_platform_hermes_v2_directory_exists():
    assert exactly_one_row_carries_the_product(flux_rows())
    assert not (ROOT / "platform" / "hermes-v2").exists(), (
        "a second copy is a second Telegram poller"
    )


def test_the_row_prunes_waits_on_the_vault_and_grades_the_gateway():
    assert the_row_is_a_real_road(_row())


def test_the_pod_runs_the_image_hermes_v2_builds_and_flux_moves_the_tag():
    kust_text = (ROW_DIR / "kustomization.yaml").read_text()
    assert the_image_is_the_products_build(
        _docs(ROW_DIR / "gateway.yaml"),
        yaml.safe_load(kust_text),
        kust_text,
        _docs(ROOT / "platform" / "image-automation" / "hermes-agent.yaml"),
    )


def test_the_catalogue_holds_the_layer_the_founder_card_and_the_company():
    assert the_catalogue_holds_it(
        _docs(ROOT / "backstage" / "platform" / "catalog-info.yaml"),
        _docs(ROOT / "backstage" / "founder" / "catalog-info.yaml"),
        (ROOT / "bin" / "catalog-gen").read_text(),
    )


def test_its_traces_reach_the_estate_with_keys_from_the_vault():
    assert its_traces_reach_the_estate(
        _docs(ROW_DIR / "gateway.yaml"), _docs(ROW_DIR / "langfuse-key.yaml")
    )


# --- the other way: a mutated copy is refused ---------------------------------------------------


def test_a_second_row_for_the_same_directory_is_refused():
    rows = flux_rows()
    twin = copy.deepcopy(_row())
    twin["metadata"]["name"] = "hermes-v2"
    assert not exactly_one_row_carries_the_product(rows + [twin])
    twin["metadata"]["name"] = "otto"
    assert not exactly_one_row_carries_the_product(rows + [twin])


def test_a_row_that_neither_prunes_nor_grades_the_gateway_is_refused():
    row = copy.deepcopy(_row())
    row["spec"]["prune"] = False
    assert not the_row_is_a_real_road(row)
    row = copy.deepcopy(_row())
    row["spec"]["healthChecks"] = []
    assert not the_row_is_a_real_road(row)


def test_a_pod_on_another_image_or_a_tag_flux_does_not_move_is_refused():
    kust_text = (ROW_DIR / "kustomization.yaml").read_text()
    kust = yaml.safe_load(kust_text)
    auto = _docs(ROOT / "platform" / "image-automation" / "hermes-agent.yaml")
    docs = _docs(ROW_DIR / "gateway.yaml")
    (dep,) = [d for d in docs if d["kind"] == "Deployment"]
    (gw,) = [
        c
        for c in dep["spec"]["template"]["spec"]["containers"]
        if c["name"] == "gateway"
    ]
    gw["image"] = "ghcr.io/chidionyema/hermes-v2"
    assert not the_image_is_the_products_build(docs, kust, kust_text, auto)
    gw["image"] = IMAGE
    assert not the_image_is_the_products_build(
        docs, kust, kust_text.replace("$imagepolicy", "pinned-by-hand"), auto
    )


def test_a_catalogue_that_forgets_the_row_or_the_product_repo_is_refused():
    plat = _docs(ROOT / "backstage" / "platform" / "catalog-info.yaml")
    founder = _docs(ROOT / "backstage" / "founder" / "catalog-info.yaml")
    gen = (ROOT / "bin" / "catalog-gen").read_text()
    broken = copy.deepcopy(plat)
    (layer,) = [
        e
        for e in broken
        if e["kind"] == "Component" and e["metadata"]["name"] == "layer-hermes-agent"
    ]
    del layer["metadata"]["annotations"]["estate/flux-kustomization"]
    assert not the_catalogue_holds_it(broken, founder, gen)
    assert not the_catalogue_holds_it(
        plat, founder, gen.replace(PRODUCT_REPO, "https://example.invalid/hermes")
    )


def test_a_pod_with_no_trace_door_or_a_key_typed_in_the_env_is_refused():
    lf = _docs(ROW_DIR / "langfuse-key.yaml")
    docs = _docs(ROW_DIR / "gateway.yaml")
    (dep,) = [d for d in docs if d["kind"] == "Deployment"]
    (gw,) = [
        c
        for c in dep["spec"]["template"]["spec"]["containers"]
        if c["name"] == "gateway"
    ]
    gw["env"] = [e for e in gw["env"] if e["name"] != "LANGFUSE_BASE_URL"]
    assert not its_traces_reach_the_estate(docs, lf)
    docs = _docs(ROW_DIR / "gateway.yaml")
    (dep,) = [d for d in docs if d["kind"] == "Deployment"]
    (gw,) = [
        c
        for c in dep["spec"]["template"]["spec"]["containers"]
        if c["name"] == "gateway"
    ]
    gw["env"].append({"name": "LANGFUSE_SECRET_KEY", "value": "sk-lf-typed-here"})
    assert not its_traces_reach_the_estate(docs, lf)

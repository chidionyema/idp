"""Incident (crew#458, 2026-08-27): the estate's three MCP servers (agentgateway, github-mcp,
estate-mcp) ran in a colima VM on the founder Mac, the last platform layer that was Mac-bound, and
every ~/.claude.json pointed at 127.0.0.1:3310. crew#375 found them as nine ssh forwards nothing
could grade. This row puts agentgateway and github-mcp on the cluster behind the edge.

Rule (rung 4): the `mcp` Flux row exists, its namespace is edge-attachable, its HTTPRoute attaches
to the https-mcp listener on prospector-edge at mcp.${ESTATE_ZONE}, every Deployment the row ships
is a Flux health check, every container names the estate collector (LAW 50), no container carries a
secret in env or in a `${...}` Flux would substitute, and the vault-seed workflow can write the entry the ExternalSecret reads.
"""

import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROW = ROOT / "platform" / "mcp"
COLLECTOR = "signoz-otel-collector.observability.svc"


def docs(path: pathlib.Path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def row_docs():
    out = []
    for f in sorted(ROW.glob("*.yaml")):
        if (
            f.name == "agentgateway.yaml"
        ):  # the gateway's own config file, not a k8s object
            continue
        out.extend(docs(f))
    return out


def test_incident_crew458_the_mcp_row_is_a_flux_row_behind_the_edge():
    flux = [
        d
        for d in docs(ROOT / "clusters" / "oke" / "platform.yaml")
        if d.get("kind") == "Kustomization" and d["metadata"]["name"] == "mcp"
    ]
    assert flux, "clusters/oke/platform.yaml has no Kustomization named mcp"
    ks = flux[0]["spec"]
    assert ks["path"] == "./platform/mcp"
    assert {d["name"] for d in ks["dependsOn"]} >= {"edge", "secret-store"}

    objs = row_docs()
    ns = [d for d in objs if d["kind"] == "Namespace"][0]
    assert ns["metadata"]["labels"]["idp.estate/edge-attach"] == "true"
    assert (
        ns["metadata"]["labels"]["pod-security.kubernetes.io/enforce"] == "restricted"
    )

    route = [d for d in objs if d["kind"] == "HTTPRoute"][0]
    parent = route["spec"]["parentRefs"][0]
    assert (parent["name"], parent["namespace"], parent["sectionName"]) == (
        "prospector-edge",
        "prospector",
        "https-mcp",
    )
    assert route["spec"]["hostnames"] == ["mcp.${ESTATE_ZONE}"]

    deployments = {d["metadata"]["name"] for d in objs if d["kind"] == "Deployment"}
    checked = {h["name"] for h in ks["healthChecks"] if h["kind"] == "Deployment"}
    assert deployments and deployments == checked


def test_incident_crew458_every_container_emits_and_carries_no_literal_secret():
    seen = 0
    for d in row_docs():
        if d["kind"] != "Deployment":
            continue
        for c in d["spec"]["template"]["spec"]["containers"]:
            seen += 1
            env = {e["name"]: e for e in c.get("env", [])}
            assert COLLECTOR in env["OTEL_EXPORTER_OTLP_ENDPOINT"]["value"], c["name"]
            for name in env:  # Kyverno secrets-not-from-env-vars: a secret is a mounted file, never env
                assert not any(
                    w in name for w in ("KEY", "TOKEN", "PASSWORD", "SECRET")
                ), f"{c['name']} env {name}"
    assert (
        seen == 4
    )  # agentgateway, github-mcp, estate-mcp and its refresh-estate-state sidecar (crew#648)
    cfg = (ROW / "agentgateway.yaml").read_text()
    assert (
        COLLECTOR in cfg
        and "keyHash: sha256:" in cfg
        and "file: /run/secrets/mcp/GITHUB_MCP_TOKEN" in cfg
    )
    assert "${" not in cfg, (
        "Flux strict envsubst (crew#284) would refuse a ${...} in the gateway config"
    )


def test_incident_crew458_the_vault_entry_the_row_reads_can_be_seeded():
    es = [d for d in row_docs() if d["kind"] == "ExternalSecret"][0]
    key = es["spec"]["dataFrom"][0]["extract"]["key"]
    seed = (ROOT / ".github" / "workflows" / "vault-seed.yml").read_text()
    # crew#66 root trust (crew#575, #577): the entry is born by bin/idp-estate-seed (MCP_GATEWAY_KEY) and
    # bin/idp-github-app refresh (GITHUB_MCP_TOKEN, an hourly App token); vault-seed refuses it by name.
    assert (
        f"{key}|" in seed
        and f"put {key} " not in seed
        and "SEED_MCP_GATEWAY_KEY" not in seed
    )
    assert "MCP_GATEWAY_KEY" in (ROOT / "bin/idp-estate-seed").read_text()
    assert (
        "GITHUB_MCP_TOKEN"
        in (ROOT / "platform/github-app/token-consumers.json").read_text()
    )


def test_incident_crew458_api_key_marker_needs_a_strict_hashed_policy_both_ways():
    """The front-door gates accept `idp.estate/auth: api-key` only with the proof beside it."""
    from test_front_door_every_route_is_behind_the_one_login import api_key_enforced

    cfg = (ROW / "agentgateway.yaml").read_text()
    assert api_key_enforced(cfg)
    assert not api_key_enforced(cfg.replace("mode: strict", "mode: optional"))
    assert not api_key_enforced(cfg.replace("keyHash: sha256:", "key: "))
    route = yaml.safe_load((ROW / "httproute.yaml").read_text())
    assert route["metadata"]["annotations"]["idp.estate/auth"] == "api-key"


def test_incident_crew458_estate_mcp_serves_the_cloud_estate_db():
    """row 3 — the estate server runs on the cluster from the artifact the cloud render publishes; the Mac mount is gone."""
    cfg = (ROW / "agentgateway.yaml").read_text()
    assert "exact: /estate/mcp" in cfg and "http://estate-mcp.mcp.svc:8001/-/mcp" in cfg
    dep = [
        d
        for d in row_docs()
        if d["kind"] == "Deployment" and d["metadata"]["name"] == "estate-mcp"
    ][0]
    init = dep["spec"]["template"]["spec"]["initContainers"][0]
    assert init["image"].startswith("ghcr.io/fluxcd/flux-cli:")
    assert "oci://ghcr.io/chidionyema/idp/estate-db:latest" in init["args"]
    main = dep["spec"]["template"]["spec"]["containers"][0]
    assert "/data/estate.db" in main["args"] and "-i" in main["args"]
    assert {v["name"] for v in dep["spec"]["template"]["spec"]["volumes"]} == {
        "data",
        "creds",
        "tmp",
    }  # tmp: writable /tmp under readOnlyRootFilesystem (crash-loop 2026-08-27 20:30Z)
    ks = yaml.safe_load((ROW / "kustomization.yaml").read_text())
    assert (
        "estate-mcp.yaml" in ks["resources"] and "pull-secret.yaml" in ks["resources"]
    )
    assert ks["images"][0]["name"] == "ghcr.io/chidionyema/estate-mcp"
    wf = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "catalog-render.yml").read_text()
    )
    steps = wf["jobs"]["render"]["steps"]
    assert any("bin/idp-estate-db-push" in (s.get("run") or "") for s in steps)
    assert (ROOT / "bin" / "idp-estate-db-push").exists()
    flux = [
        d
        for d in docs(ROOT / "clusters" / "oke" / "platform.yaml")
        if d.get("kind") == "Kustomization" and d["metadata"]["name"] == "mcp"
    ][0]
    hcs = [
        {k: h[k] for k in ("kind", "name", "namespace")}
        for h in flux["spec"]["healthChecks"]
    ]
    assert {"kind": "Deployment", "name": "estate-mcp", "namespace": "mcp"} in hcs

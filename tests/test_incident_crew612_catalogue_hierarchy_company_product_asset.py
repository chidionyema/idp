"""crew#612 CP2: the catalogue reads Bytesync -> company -> product -> asset. Measured
2026-08-29 before this change on the 2026-08-28 inventory: 1 Domain (platform), 1 System
(estate) plus stacks, and every one of the 336 assets on the one System -- one flat list.

Rule, proved on the fixture inventory the way CI renders it: an organization Group above
the platform team; a Domain per company; a product System per tracked repository whose
domain is a company that exists; every Component and Resource on a System that exists.
"""
import os
import pathlib
import subprocess
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"
FIX = ROOT / "tests" / "fixtures" / "inventory.json"


def _render(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    r = subprocess.run([sys.executable, str(GEN)],
                       env={**os.environ, "INV": str(FIX), "OUT": str(out), "ESTATE_ENV": "dev",
                            "CATALOG_GEN_ROOT": str(ROOT)},
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return [d for d in yaml.safe_load_all((out / "catalog-info.yaml").read_text()) if d]


def test_every_asset_is_reachable_from_a_company_through_a_product(tmp_path):
    docs = _render(tmp_path)
    groups = {d["metadata"]["name"]: d for d in docs if d["kind"] == "Group"}
    assert groups["bytesync"]["spec"]["type"] == "organization"
    assert groups["platform"]["spec"]["parent"] == "group:default/bytesync"
    domains = {d["metadata"]["name"] for d in docs if d["kind"] == "Domain"}
    assert {"mumchimp", "prospector", "hermes-v2", "platform"} <= domains
    systems = {d["metadata"]["name"]: d["spec"]["domain"] for d in docs if d["kind"] == "System"}
    assert [n for n, dm in systems.items() if dm not in domains] == []
    repos = [d["metadata"]["name"] for d in docs if d["kind"] == "Component" and d["spec"]["type"] == "service"]  # catalog-gen MAP: repo -> Component/service
    assert repos, "fixture has no repository rows"
    assert all(f"product-{r}" in systems for r in repos), repos
    assets = [d for d in docs if d["kind"] in ("Component", "Resource")]
    unreachable = [d["metadata"]["name"] for d in assets
                   if d["spec"].get("system", "").split("/")[-1] not in systems]
    assert not unreachable, unreachable
    # An asset the inventory places inside a repository (dependsOn its Component) sits on
    # that repository's product, never on the estate catch-all; a repository sits on its own.
    repo_set = set(repos)
    for d in assets:
        inside = [t.split("/")[-1] for t in d["spec"].get("dependsOn", []) if t.startswith("component:default/")]
        inside = [t for t in inside if t in repo_set]
        if d["metadata"]["name"] in repo_set:
            assert d["spec"]["system"] == f"system:default/product-{d['metadata']['name']}", d["metadata"]["name"]
        elif inside:
            assert d["spec"]["system"] == f"system:default/product-{inside[0]}", (d["metadata"]["name"], d["spec"]["system"])
    assert any(d["spec"].get("dependsOn") for d in assets if d["metadata"]["name"] not in repo_set), "fixture proves nothing: no asset inside a repo"


def test_company_placement_is_by_repository_name_and_defaults_to_platform():
    import importlib.machinery, importlib.util
    spec = importlib.util.spec_from_loader("catalog_gen", importlib.machinery.SourceFileLoader("catalog_gen", str(GEN)))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    assert m.company_of("prospector-main") == "prospector"
    assert m.company_of("hermes-v2") == "hermes-v2"
    assert m.company_of("mumchimp-medusa") == "mumchimp"
    assert m.company_of("idp") == "platform" and m.company_of("") == "platform"

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


def _render(tmp_path, inv=None):
    out = tmp_path / "out"
    out.mkdir(parents=True)
    r = subprocess.run([sys.executable, str(GEN)],
                       env={**os.environ, "INV": str(inv or FIX), "OUT": str(out), "ESTATE_ENV": "dev",
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


def test_every_company_product_and_group_carries_a_link_a_person_can_open(tmp_path):
    """crew#612 CP2: 'every entity has description, owner, system and links'. Measured on
    the live inventory before this: Domain 0 of 4, System 0 of 15, Group 0 of 2 had a link.
    A Domain links to its repositories (or, for a company whose code is not checked out
    here, to where it is live); a product System links to its repository; the org Group
    to the GitHub owner. Assets inside a tracked repository link to the file on the
    default branch (tree/HEAD) and only when git tracks that path, so no link 404s."""
    docs = _render(tmp_path)
    for d in docs:
        if d["kind"] in ("Domain", "System", "Group"):
            links = d["metadata"].get("links") or []
            assert links, f"{d['kind']} {d['metadata']['name']} has no link"
            # absolute, or a path inside this portal (a stack System filters the catalogue)
            assert all(l["url"].startswith(("http", "/catalog")) for l in links), links
    # The fixture's repositories are not real checkouts, so nothing above can carry a code
    # link (git tracks no path there); a real one-file repository proves the asset link.
    import json
    repo = tmp_path / "realrepo"
    repo.mkdir()
    (repo / "tracked.sqlite").write_text("x")
    (repo / "untracked.sqlite").write_text("y")
    for cmd in (["git", "init", "-q"], ["git", "add", "tracked.sqlite"],
                ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t"]):
        subprocess.run(cmd, cwd=repo, check=True, capture_output=True)
    inv = json.loads(FIX.read_text())
    inv["rows"] += [
        {"id": "realrepo", "kind": "repo", "root": "a", "path": str(repo), "coupling": None,
         "remote": "https://github.com/example/realrepo.git"},
        {"id": "tracked.sqlite", "kind": "ledger", "root": "a", "path": str(repo / "tracked.sqlite"), "coupling": None},
        {"id": "untracked.sqlite", "kind": "ledger", "root": "a", "path": str(repo / "untracked.sqlite"), "coupling": None},
    ]
    inv_path = tmp_path / "inventory.json"
    inv_path.write_text(json.dumps(inv))
    docs = _render(tmp_path / "second", inv_path)
    links = {d["metadata"]["name"]: [l["url"] for l in d["metadata"].get("links") or []]
             for d in docs if d["kind"] == "Resource"}
    tracked = [n for n in links if n.endswith("tracked.sqlite") and "untracked" not in n]
    untracked = [n for n in links if n.endswith("untracked.sqlite")]
    assert tracked and untracked, list(links)
    assert links[tracked[0]] == ["https://github.com/example/realrepo/tree/HEAD/tracked.sqlite"], links[tracked[0]]
    assert links[untracked[0]] == [], "an untracked path would 404; it must carry no code link"

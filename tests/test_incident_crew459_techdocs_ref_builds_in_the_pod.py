"""Incident test (rung 4), crew#459: the Docs section of the portal was empty.

The generator annotated every repo with a mkdocs.yml as `dir:.`, a reference
only the laptop that ran the generator can resolve. The portal runs in a pod
that has no such directory, so no docs were ever built. The rule: a repo with
a GitHub remote and a mkdocs.yml carries a `url:` techdocs-ref the pod can
fetch; `dir:.` survives only for a repo with no GitHub remote.
"""
import json
import os
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
GEN = ROOT / "bin" / "catalog-gen"


def _gen(tmp_path, repos):
    for r in repos:
        p = pathlib.Path(r["path"])
        p.mkdir(parents=True, exist_ok=True)
        if r.pop("_mkdocs", False):
            (p / "mkdocs.yml").write_text("site_name: x\n")
    inv = tmp_path / "inv.json"
    inv.write_text(json.dumps({"at": "2026-08-27T00:00:00Z", "findings": [], "rows": repos}))
    out = tmp_path / "out"
    out.mkdir()
    res = subprocess.run([str(GEN)], env={**os.environ, "INV": str(inv), "OUT": str(out),
                                          "ESTATE_ENV": "dev", "CATALOG_GEN_ROOT": str(tmp_path)},
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    refs = {}
    for f in out.rglob("*.yaml"):
        for d in yaml.safe_load_all(f.read_text()):
            if d and d.get("kind") == "Component" and d["metadata"]["name"] in ("with-docs", "no-docs", "local-docs"):
                refs[d["metadata"]["name"]] = d["metadata"].get("annotations", {}).get(
                    "backstage.io/techdocs-ref")
    return refs


def test_a_github_repo_with_mkdocs_gets_a_url_ref_the_pod_can_fetch(tmp_path):
    refs = _gen(tmp_path, [
        {"kind": "repo", "id": "with-docs", "path": str(tmp_path / "with-docs"),
         "remote": "git@github.com:example/with-docs.git", "_mkdocs": True},
        {"kind": "repo", "id": "no-docs", "path": str(tmp_path / "no-docs"),
         "remote": "git@github.com:example/no-docs.git"},
        {"kind": "repo", "id": "local-docs", "path": str(tmp_path / "local-docs"),
         "remote": None, "_mkdocs": True},
    ])
    assert refs["with-docs"] == "url:https://github.com/example/with-docs/tree/main/"
    assert refs["no-docs"] is None
    assert refs["local-docs"] == "dir:."
    assert [k for k, v in refs.items() if v == "dir:."] == ["local-docs"]

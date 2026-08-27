"""Incident test, crew#412 row 1: a founder entity's Docs tab must open.

Founder, 2026-08-27: "why cant we have founders dashboard in backstage rather than nother ui".
A techdocs-ref that points at a repo without mkdocs.yml is a Docs tab that says "not found" in
the one portal he is meant to use, so the rule is: every techdocs-ref on a founder entity names a
tree whose root holds mkdocs.yml, and the pod can build it (generator runIn local, generator in
the image). BLIND when GitHub cannot be reached, never green by absence.
"""
import pathlib
import re
import subprocess

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOUNDER = ROOT / "backstage" / "founder" / "catalog-info.yaml"


def _refs() -> list[tuple[str, str]]:
    out = []
    for doc in yaml.safe_load_all(FOUNDER.read_text()):
        if not doc:
            continue
        ref = (doc.get("metadata", {}).get("annotations") or {}).get("backstage.io/techdocs-ref")
        if ref:
            out.append((doc["metadata"]["name"], ref))
    return out


def test_the_crew_board_has_a_docs_tab():
    assert any(name == "founder-crew-board" for name, _ in _refs()), "founder-crew-board carries no techdocs-ref"


@pytest.mark.parametrize("name,ref", _refs() or [("none", "")])
def test_every_founder_techdocs_ref_names_a_tree_with_a_manifest(name: str, ref: str):
    if not ref:
        pytest.skip("no techdocs-ref on any founder entity")
    m = re.fullmatch(r"url:https://github\.com/([^/]+)/([^/]+)/tree/([^/]+)/?", ref)
    assert m, f"{name}: techdocs-ref {ref!r} is not url:https://github.com/<owner>/<repo>/tree/<ref>/"
    owner, repo, gitref = m.groups()
    r = subprocess.run(["gh", "api", f"repos/{owner}/{repo}/contents/mkdocs.yml?ref={gitref}", "--jq", ".name"],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0 and ("Could not resolve" in r.stderr or "network" in r.stderr.lower() or "auth" in r.stderr.lower()):
        pytest.skip(f"BLIND: gh api unreachable: {r.stderr.strip()[:120]}")
    assert r.returncode == 0 and r.stdout.strip() == "mkdocs.yml", f"{name}: {owner}/{repo}@{gitref} has no mkdocs.yml at its root ({r.stderr.strip()[:120]})"


def test_the_pod_can_build_docs_without_docker():
    cfg = yaml.safe_load((ROOT / "backstage" / "app-config.yaml").read_text())
    assert cfg["techdocs"]["generator"]["runIn"] == "local"
    dockerfile = (ROOT / "backstage" / "Dockerfile").read_text()
    final = dockerfile[dockerfile.rindex("\nFROM "):]
    assert re.search(r"pip3? install .*mkdocs-techdocs-core==\d", final), "final image stage does not install a pinned mkdocs-techdocs-core"

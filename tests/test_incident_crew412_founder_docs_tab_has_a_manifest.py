"""Incident test, crew#412 row 1: a founder entity's Docs tab must open.

Founder, 2026-08-27: "why cant we have founders dashboard in backstage rather than nother ui".
A techdocs-ref that points at a repo without mkdocs.yml is a Docs tab that says "not found" in
the one portal he is meant to use, so the rule is: every techdocs-ref on a founder entity names a
tree whose root holds mkdocs.yml, and the pod can build it (generator runIn local, generator in
the image) into /tmp, because the catalogue root filesystem is read-only
(2026-09-02: mkdir under node_modules ENOENT on founder-gods-view). BLIND when GitHub cannot be reached, never green by absence.
"""
import pathlib
import re
import urllib.error
import urllib.request

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
    # Plain HTTPS, no gh: CI runners carry no GH_TOKEN for this job (idp#288 run 1 failed on
    # that, not on the manifest). The repo is public, so the raw file is the receipt.
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{gitref}/mkdocs.yml"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310 - fixed https host
            body = resp.read(4096).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        assert e.code != 404, f"{name}: {owner}/{repo}@{gitref} has no mkdocs.yml at its root (HTTP 404)"
        pytest.skip(f"BLIND: GitHub answered HTTP {e.code} for {url}")
    except (urllib.error.URLError, TimeoutError) as e:
        pytest.skip(f"BLIND: GitHub unreachable: {e}")
    assert "docs_dir" in body or "site_name" in body, f"{name}: {url} is not a mkdocs manifest"


def test_the_pod_can_build_docs_without_docker():
    cfg = yaml.safe_load((ROOT / "backstage" / "app-config.yaml").read_text())
    assert cfg["techdocs"]["generator"]["runIn"] == "local"
    pub = cfg["techdocs"]["publisher"]
    assert pub["type"] == "local"
    dest = pub["local"]["publishDirectory"]
    assert dest.startswith("/tmp/"), (
        f"techdocs.publisher.local.publishDirectory is {dest!r}; the catalogue "
        "pod has a read-only root filesystem and only /tmp is writable, so a "
        "publish into node_modules mkdir-fails (2026-09-02 founder-gods-view ENOENT)"
    )
    dockerfile = (ROOT / "backstage" / "Dockerfile").read_text()
    final = dockerfile[dockerfile.rindex("\nFROM "):]
    assert re.search(r"pip3? install .*mkdocs-techdocs-core==\d", final), "final image stage does not install a pinned mkdocs-techdocs-core"


def test_oke_catalogue_overrides_the_publish_dir_before_the_image_rolls():
    """The baked image still defaults to node_modules until the next backstage
    build. The OKE overlay injects the same /tmp path as an APP_CONFIG override
    so Flux can unstick live docs without waiting on that image."""
    overlay = (ROOT / "platform" / "backstage" / "overlays" / "oke" / "kustomization.yaml").read_text()
    assert "APP_CONFIG_techdocs_publisher_local_publishDirectory" in overlay, (
        "OKE catalogue overlay does not inject the TechDocs publish dir; live "
        "docs stay 404 until a new backstage image ships"
    )
    assert "/tmp/techdocs" in overlay

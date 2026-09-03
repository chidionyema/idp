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

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
FOUNDER = ROOT / "backstage" / "founder" / "catalog-info.yaml"


def _refs() -> list[tuple[str, str]]:
    out = []
    for doc in yaml.safe_load_all(FOUNDER.read_text()):
        if not doc:
            continue
        ref = (doc.get("metadata", {}).get("annotations") or {}).get(
            "backstage.io/techdocs-ref"
        )
        if ref:
            out.append((doc["metadata"]["name"], ref))
    return out


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
    final = dockerfile[dockerfile.rindex("\nFROM ") :]
    assert re.search(r"pip3? install .*mkdocs-techdocs-core==\d", final), (
        "final image stage does not install a pinned mkdocs-techdocs-core"
    )

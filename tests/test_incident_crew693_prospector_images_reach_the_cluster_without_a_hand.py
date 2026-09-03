"""crew#693: prod ran prospector-store-web f398a66 (built 2026-08-26) while prospector main was
a6223ef. CI built every merge; nothing moved the tag: the overlay pinned it by hand and no
ImagePolicy existed for prospector. Merged was inventory, not released.

The guard: every image the prospector Kustomization overrides has an ImagePolicy of the estate's
orderable shape, carries the automation marker, and the one automation walks the path that holds it.
"""

from __future__ import annotations

import pathlib
import re

import yaml

IDP = pathlib.Path(__file__).resolve().parents[1]
EDGE = IDP / "clusters" / "oke" / "edge.yaml"
AUTOMATION_DIR = IDP / "platform" / "image-automation"
MARKER = re.compile(
    r'#\s*\{"\$imagepolicy":\s*"flux-system:(?P<policy>[a-z0-9-]+):tag"\}'
)
ORDERABLE = "^main-(?P<run>[0-9]+)-[0-9a-f]{40}$"


def _docs(path: pathlib.Path) -> list[dict]:
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def _prospector_kustomization() -> dict:
    for d in _docs(EDGE):
        if d.get("kind") == "Kustomization" and d["metadata"]["name"] == "prospector":
            return d
    raise AssertionError(
        "clusters/oke/edge.yaml has no Flux Kustomization named prospector"
    )


def _policies() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in AUTOMATION_DIR.glob("*.yaml"):
        for d in _docs(f):
            if d.get("kind") == "ImagePolicy":
                out[d["metadata"]["name"]] = d
    return out


def _markers_in_edge() -> dict[str, str]:
    found: dict[str, str] = {}
    for line in EDGE.read_text().splitlines():
        m = MARKER.search(line)
        if m:
            image = line.split("newTag:")[0]
            found[m.group("policy")] = image
    return found


def test_every_overridden_prospector_image_has_an_orderable_image_policy():
    images = _prospector_kustomization()["spec"].get("images", [])
    assert images, (
        "the prospector Kustomization overrides no image: the tag is back in a hand"
    )
    policies = _policies()
    for entry in images:
        name = entry["name"].rsplit("/", 1)[-1]
        assert name in policies, (
            f"{entry['name']} has no ImagePolicy in platform/image-automation"
        )
        assert policies[name]["spec"]["filterTags"]["pattern"] == ORDERABLE, name
        assert policies[name]["spec"]["policy"] == {"numerical": {"order": "asc"}}, name


def test_every_overridden_prospector_image_carries_the_automation_marker():
    images = {
        e["name"].rsplit("/", 1)[-1]
        for e in _prospector_kustomization()["spec"]["images"]
    }
    assert images <= set(_markers_in_edge()), (images, _markers_in_edge())


def test_the_one_automation_walks_the_path_that_holds_the_markers():
    automations = [
        d
        for f in AUTOMATION_DIR.glob("*.yaml")
        for d in _docs(f)
        if d.get("kind") == "ImageUpdateAutomation"
    ]
    assert len(automations) == 1, [a["metadata"]["name"] for a in automations]
    path = automations[0]["spec"]["update"]["path"].rstrip("/") or "."
    rel = EDGE.relative_to(IDP).as_posix()
    assert path in (".", "./") or rel.startswith(path.removeprefix("./")), (path, rel)

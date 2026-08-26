"""Incident (crew#284, idp#262/#263, 2026-08-26 23:2xZ): `platform/llm/postgres.yaml` named its image
`postgres:17.6-alpine`. The OKE node runtime enforces short-name mode and the pod never started:
`ImageInspectError: short name mode is enforcing, but image name postgres:17.6-alpine returns
ambiguous list`. CI was green; Kyverno render passed; nothing checked that an image names its registry.

Rule (rung 2, a property over every Kustomization clusters/* applies): every `image:` a Kustomization
applies is fully qualified: its first path component is a registry host (contains a dot, a port, or is
`localhost`). A kustomization `images:` override with `newName` is the effective name.
"""
import glob
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
# `image:` followed by a value on the same line; a bare `image:` heading a Helm-values mapping
# (`image:\n  repository: ...`) has no value and is not an image reference.
IMAGE = re.compile(r"^\s*(?:-\s*)?image:[ \t]+['\"]?([^'\"\s#]+)[ \t]*(?:#.*)?$", re.M)


def fully_qualified(image: str) -> bool:
    """Pure: does the image name its registry?"""
    first = image.split("/", 1)[0]
    return "/" in image and ("." in first or ":" in first or first == "localhost")


def effective_images(path: pathlib.Path) -> dict[str, str]:
    """image -> file, after applying `images:` overrides from kustomization.yaml files under path."""
    overrides = {}
    for k in glob.glob(str(path / "**" / "kustomization.yaml"), recursive=True):
        for o in (yaml.safe_load(pathlib.Path(k).read_text()) or {}).get("images", []) or []:
            if o.get("newName"):
                overrides[o["name"]] = o["newName"]
    found = {}
    for f in glob.glob(str(path / "**" / "*.yaml"), recursive=True):
        for img in IMAGE.findall(pathlib.Path(f).read_text()):
            name = img.rsplit(":", 1)[0] if "@" not in img else img.split("@", 1)[0]
            found[overrides.get(name, img)] = str(pathlib.Path(f).relative_to(ROOT))
    return found


def test_every_applied_image_names_its_registry():
    bad = {}
    for f in glob.glob(str(ROOT / "clusters" / "*" / "*.yaml")):
        for d in yaml.safe_load_all(pathlib.Path(f).read_text()):
            if d and d.get("kind") == "Kustomization" and d["spec"].get("path", "").startswith("./platform"):
                for img, src in effective_images(ROOT / d["spec"]["path"]).items():
                    if not fully_qualified(img):
                        bad[img] = src
    assert not bad, f"short image names the node runtime refuses (ImageInspectError): {bad}"


def test_guard_refuses_the_incident_and_permits_qualified_names():
    assert not fully_qualified("postgres:17.6-alpine")
    assert not fully_qualified("berriai/litellm:v1.98.0")
    assert fully_qualified("docker.io/library/postgres:17.6-alpine")
    assert fully_qualified("ghcr.io/berriai/litellm-database:v1.98.0")
    assert fully_qualified("localhost:5000/idp/backstage:local")

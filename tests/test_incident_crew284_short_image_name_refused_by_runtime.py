"""Incident (crew#284, idp#262/#263, 2026-08-26 23:2xZ): `platform/llm/postgres.yaml` named its image
`postgres:17.6-alpine`. The OKE node runtime enforces short-name mode and the pod never started:
`ImageInspectError: short name mode is enforcing, but image name postgres:17.6-alpine returns
ambiguous list`. CI was green; Kyverno render passed; nothing checked that an image names its registry.

Rule (rung 2, a property over every Kustomization clusters/* applies): every `image:` a Kustomization
applies is fully qualified: its first path component is a registry host (contains a dot, a port, or is
`localhost`). A kustomization `images:` override with `newName` is the effective name.
Second instance (crew#396, 2026-08-27 03:02Z receipt): the temporal HelmRelease shipped the chart's
default `temporalio/server`, `temporalio/admin-tools`, `temporalio/ui`; every temporal pod stayed
Pending on the same ImageInspectError and the HelmRelease failed on a stalled frontend. The guard
only read `image:` lines, so a chart image named through `repository:` in HelmRelease values was
invisible. Now every `repository:` value is graded the same way. Residual: a chart default that the
HelmRelease does not override is not in any file here and stays unseen; name the registry for every
image a chart runs.
"""
import glob
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
# `image:` followed by a value on the same line; a bare `image:` heading a Helm-values mapping
# (`image:\n  repository: ...`) has no value and is not an image reference. A value opening `[`
# or `{` is a YAML flow collection, never an image name: the router's fallback chain
# `- image: [image-or]` in platform/llm/config.yaml (2026-08-30) is a lane called "image" and
# was read here as a container image called "[image-or]". A container image reference is always
# a scalar, so excluding the two flow openers costs no coverage.
IMAGE = re.compile(r"^\s*(?:-\s*)?image:[ \t]+['\"]?(?![\[{])([^'\"\s#]+)[ \t]*(?:#.*)?$", re.M)
# Helm values name an image as `image: { repository: x }` or `repository: x` under `image:`; the
# repository alone is the name the runtime resolves, so it is graded exactly like `image:`.
REPOSITORY = re.compile(r"repository:[ \t]+['\"]?([^'\"\s#}]+)", re.M)


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
        text = pathlib.Path(f).read_text()
        for img in IMAGE.findall(text) + [r + "/" if "/" not in r else r for r in REPOSITORY.findall(text)]:
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


def test_a_yaml_flow_value_is_not_an_image_name(tmp_path):
    """A router fallback chain is `image: [image-or]`; a container image is always a scalar."""
    p = tmp_path / "config.yaml"
    p.write_text("fallbacks:\n  - image: [image-or]\n  - other: [a, b]\n")
    assert IMAGE.findall(p.read_text()) == []
    p.write_text("containers:\n  - image: docker.io/library/postgres:17.6-alpine\n")
    assert IMAGE.findall(p.read_text()) == ["docker.io/library/postgres:17.6-alpine"]
    # crew#396: the second instance, a chart image named by `repository:` in HelmRelease values
    assert REPOSITORY.findall("    image: { repository: temporalio/server }\n") == ["temporalio/server"]
    assert not fully_qualified("temporalio/server")
    assert fully_qualified("docker.io/temporalio/server")


def test_incident_crew396_temporal_chart_images_name_their_registry():
    text = (ROOT / "platform" / "temporal" / "temporal.yaml").read_text()
    repos = REPOSITORY.findall(text)
    assert sorted(repos) == ["docker.io/temporalio/admin-tools", "docker.io/temporalio/server",
                             "docker.io/temporalio/ui"], repos

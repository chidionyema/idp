"""Incident, 2026-08-25 (idp#125): the first Backstage image build was red on
Trivy CRITICAL CVE-2026-59873 in three copies of node-tar 6.2.1: two under the
app's node_modules (cacache, node-gyp) and npm's own copy in the base image.

Rung 4, incident test. The rule, not the code: every `tar` the lockfile
resolves is a fixed version, the runtime stage removes npm, and bin/dockerfiles
discovers backstage/Dockerfile while skipping its .dockerignore twin.
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED = (7, 5, 19)


def _version(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def test_every_resolved_tar_is_at_or_past_the_fix():
    lock = (ROOT / "backstage" / "yarn.lock").read_text()
    versions = re.findall(r'^"tar@[^"]*":\n  version: ([0-9.]+)', lock, re.M)
    assert versions, "no tar entry found in yarn.lock"
    bad = [v for v in versions if _version(v) < FIXED]
    assert not bad, f"tar below {FIXED}: {bad}"
    resolutions = json.loads((ROOT / "backstage" / "package.json").read_text())["resolutions"]
    assert "tar" in resolutions, "resolutions.tar missing: the pin would drift on the next install"


def test_runtime_stage_removes_npm():
    text = (ROOT / "backstage" / "Dockerfile").read_text()
    runtime = text.split("# --- stage 4")[1]
    assert "rm -rf /usr/local/lib/node_modules/npm" in runtime


def test_dockerfiles_discovers_backstage_and_skips_its_dockerignore():
    out = subprocess.run([str(ROOT / "bin" / "dockerfiles"), "--json"], check=True,
                         capture_output=True, text=True, cwd=ROOT).stdout
    files = {d["dockerfile"] for d in json.loads(out)}
    assert "backstage/Dockerfile" in files
    assert not any(f.endswith(".dockerignore") for f in files), files


def test_container_origin_comes_from_the_overlay_not_the_config():
    """Review on idp#125: a literal localhost baseUrl in the container config broke every
    browser catalog call on the cluster. The config reads APP_BASE_URL; the OKE overlay sets it."""
    cfg = (ROOT / "backstage" / "app-config.container.yaml").read_text()
    assert re.findall(r"^\s*baseUrl: (.*)$", cfg, re.M) == ["${APP_BASE_URL}"] * 2
    overlay = (ROOT / "platform" / "backstage" / "overlays" / "oke" / "kustomization.yaml").read_text()
    assert "name: APP_BASE_URL" in overlay


def test_guest_outside_development_only_while_no_public_route_exists():
    """dangerouslyAllowOutsideDevelopment makes anyone who reaches the port a signed-in user.
    It is acceptable only while the Service is ClusterIP and platform/edge has no route to it."""
    cfg = (ROOT / "backstage" / "app-config.container.yaml").read_text()
    if "dangerouslyAllowOutsideDevelopment: true" not in cfg:
        return
    edge = "".join(p.read_text() for p in (ROOT / "platform" / "edge").glob("*.yaml"))
    assert "catalogue" not in edge and "backstage" not in edge, "a route exists: put OIDC in front or turn the flag off"
    base = (ROOT / "platform" / "backstage" / "base" / "catalogue.yaml").read_text()
    assert "type: ClusterIP" in base


def test_oke_overlay_pulls_an_image_build_multiarch_actually_pushes():
    """Incident 2026-08-25: the overlay named ghcr.io/chidionyema/idp/backstage:main; the workflow
    pushes ghcr.io/chidionyema/<name>:<sha> only (build-multiarch.yml header). ImagePullBackOff."""
    import re
    import yaml
    k = yaml.safe_load((ROOT / "platform/backstage/overlays/oke/kustomization.yaml").read_text())
    names = {line.split()[0] for line in subprocess.run(["bin/dockerfiles"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines() if line.strip()}
    ours = [img for img in k["images"] if not img["newName"].startswith("docker.io/")]  # postgres is upstream
    assert ours, "no estate image in the overlay"
    for img in ours:
        assert img["newName"].startswith("ghcr.io/chidionyema/"), img
        assert img["newName"].rsplit("/", 1)[1] in names, f"{img['newName']}: not an image bin/dockerfiles produces ({sorted(names)})"
        assert re.fullmatch(r"[0-9a-f]{40}", str(img.get("newTag", ""))), f"{img}: tag is not a commit sha"

"""Every ImagePolicy in platform/image-automation must reach the cluster.

2026-09-26: c96359f4b cut clusters/oke/ from ~80 Flux rows to 7 and took the image-automation row
with it. Policies already in the cluster kept working as orphans, so nothing looked broken, but
every policy added afterwards (voice-router's) was never applied: voice in OKE stayed on a
crashing image for three days.

This grades what Flux would apply: `kustomize build` of the cluster root must emit a Flux
Kustomization pointed at platform/image-automation, and `kustomize build` of that directory must
emit voice-router's ImagePolicy.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    shutil.which("kustomize") is None, reason="kustomize not installed"
)


def _rendered(path: str) -> list[dict]:
    out = subprocess.run(
        ["kustomize", "build", str(ROOT / path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def test_the_cluster_root_renders_a_flux_row_for_platform_image_automation():
    paths = {
        d["spec"]["path"].lstrip("./")
        for d in _rendered("clusters/oke")
        if d.get("kind") == "Kustomization"
        and d.get("apiVersion", "").startswith("kustomize.toolkit.fluxcd.io")
    }
    assert "platform/image-automation" in paths


def test_platform_image_automation_renders_voice_routers_image_policy():
    names = {
        d["metadata"]["name"]
        for d in _rendered("platform/image-automation")
        if d.get("kind") == "ImagePolicy"
    }
    assert "voice-router" in names

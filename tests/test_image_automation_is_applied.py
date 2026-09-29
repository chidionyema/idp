"""Every ImagePolicy in platform/image-automation must reach the cluster.

2026-09-26: c96359f4b cut clusters/oke/ from ~80 Flux rows to 7 and took the image-automation row
with it. Policies already in the cluster kept working as orphans, so nothing looked broken, but
every policy added afterwards (voice-router's) was never applied: voice in OKE stayed on a
crashing image for three days. This holds the row in place and pointed at the directory.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CLUSTER = ROOT / "clusters/oke"


def _docs(path: Path):
    return [d for d in yaml.safe_load_all(path.read_text()) if d]


def test_a_flux_row_applies_platform_image_automation():
    listed = _docs(CLUSTER / "kustomization.yaml")[0]["resources"]
    rows = [
        d
        for f in listed
        if f.endswith(".yaml") and (CLUSTER / f).is_file()
        for d in _docs(CLUSTER / f)
        if d.get("kind") == "Kustomization"
    ]
    paths = {d["spec"]["path"].lstrip("./") for d in rows}
    assert "platform/image-automation" in paths


def test_voice_router_has_an_image_policy_in_that_directory():
    listed = _docs(ROOT / "platform/image-automation/kustomization.yaml")[0][
        "resources"
    ]
    assert "voice-router.yaml" in listed

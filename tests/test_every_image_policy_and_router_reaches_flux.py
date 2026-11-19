"""idp#8067: a merged router or ImagePolicy that no Kustomization names never runs.

PennyD was given an ImagePolicy (#8285) and ACG one before it, yet
platform/image-automation/kustomization.yaml named neither, so no build could move either
deployment. The class -- a manifest in a Flux path no Kustomization reconciles -- is held here
for every ImagePolicy, not one instance.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
IMAGE_AUTOMATION = ROOT / "platform" / "image-automation"


def _resources(kustomization: Path) -> set[str]:
    doc = yaml.safe_load(kustomization.read_text())
    return {str(r).rstrip("/").removeprefix("./") for r in doc.get("resources", [])}


def test_every_image_automation_manifest_is_applied() -> None:
    named = _resources(IMAGE_AUTOMATION / "kustomization.yaml")
    on_disk = {
        p.name
        for p in IMAGE_AUTOMATION.glob("*.yaml")
        if p.name != "kustomization.yaml"
    }
    unapplied = sorted(on_disk - named)
    assert not unapplied, f"ImagePolicy files no Kustomization applies: {unapplied}"

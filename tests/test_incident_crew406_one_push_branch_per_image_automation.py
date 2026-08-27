"""Incident crew#406, 2026-08-27: two ImageUpdateAutomations (backstage, sovereign-worker) pushed to
the same branch flux/image-updates. The first push landed (a9aacd9, Flux's first commit); the
second failed forever with `cannot lock ref 'refs/heads/flux/image-updates': reference already
exists`. The rule: no two ImageUpdateAutomations share a push branch on the same repository; one
automation walks the whole platform tree for every ImagePolicy marker instead.
"""
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "platform" / "image-automation"


def _automations(files) -> list[dict]:
    return [d for f in files for d in yaml.safe_load_all(f.read_text()) if d and d.get("kind") == "ImageUpdateAutomation"]


def shared_push_branches(automations: list[dict]) -> list[str]:
    """Push targets (source/branch) claimed by more than one automation."""
    c = Counter(f"{a['spec']['sourceRef']['name']}/{a['spec']['git']['push']['branch']}" for a in automations)
    return sorted(k for k, n in c.items() if n > 1)


def _marker_files() -> list[Path]:
    return sorted(p for p in (ROOT / "platform").rglob("*.yaml") if "$imagepolicy" in p.read_text())


def test_no_two_automations_share_a_push_branch() -> None:
    autos = _automations(sorted(DIR.glob("*.yaml")))
    assert autos
    assert shared_push_branches(autos) == []


def test_every_imagepolicy_marker_is_under_an_automation_path() -> None:
    autos = _automations(sorted(DIR.glob("*.yaml")))
    paths = [(ROOT / a["spec"]["update"]["path"]).resolve() for a in autos]
    markers = _marker_files()
    assert markers, "no $imagepolicy marker under platform"
    for m in markers:
        assert any(m.resolve().is_relative_to(p) for p in paths), (m, paths)


def test_the_rule_refuses_the_pair_that_collided() -> None:
    def auto(name, branch):
        return {"kind": "ImageUpdateAutomation", "metadata": {"name": name},
                "spec": {"sourceRef": {"name": "idp-writer"}, "git": {"push": {"branch": branch}}}}
    assert shared_push_branches([auto("backstage", "flux/image-updates"), auto("sovereign-worker", "flux/image-updates")]) == ["idp-writer/flux/image-updates"]
    assert shared_push_branches([auto("backstage", "flux/image-updates")]) == []

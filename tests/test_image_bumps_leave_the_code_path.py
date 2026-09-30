"""crew#987 CP6: image bumps land on flux/deploy and never start a workflow.

342 of 406 commits on main in the 48 hours to 2026-09-30 were image bumps, each graded by the
full suite in the code queue. platform/image-automation/deploy.yaml writes them to flux/deploy
instead. These tests read the real manifests and the real workflow triggers.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEPLOY_BRANCH = "flux/deploy"


def _docs(path: str) -> list[dict]:
    return [d for d in yaml.safe_load_all((ROOT / path).read_text()) if d]


def _glob(pattern: str, ref: str) -> bool:
    """GitHub's branch-filter glob: `**` crosses `/`, `*` does not."""
    rx = (
        re.escape(pattern)
        .replace(r"\*\*", "\0")
        .replace(r"\*", "[^/]*")
        .replace("\0", ".*")
    )
    return re.fullmatch(rx, ref) is not None


def _fires_on_push(on: dict, ref: str) -> bool:
    if "push" not in on:
        return False
    cfg = on["push"] or {}
    if "branches" in cfg:
        verdict = False
        for p in cfg["branches"]:
            if _glob(p.lstrip("!"), ref):
                verdict = not p.startswith("!")
        return verdict
    if "branches-ignore" in cfg:
        return not any(_glob(p, ref) for p in cfg["branches-ignore"])
    # `tags:` alone filters to tag pushes only; anything else fires on every branch.
    return "tags" not in cfg


def _workflows_fired_by_push(ref: str) -> list[str]:
    fired = []
    for f in sorted((ROOT / ".github/workflows").glob("*.y*ml")):
        doc = yaml.safe_load(f.read_text()) or {}
        on = doc.get(True, doc.get("on")) or {}
        if isinstance(on, str):
            on = {on: None}
        if isinstance(on, list):
            on = {k: None for k in on}
        if _fires_on_push(on, ref):
            fired.append(f.name)
    return fired


def test_the_deploy_automation_rebuilds_flux_deploy_from_main():
    (auto,) = [
        d
        for d in _docs("platform/image-automation/deploy.yaml")
        if d["kind"] == "ImageUpdateAutomation"
    ]
    git = auto["spec"]["git"]
    assert git["checkout"]["ref"]["branch"] == "main"
    assert git["push"]["branch"] == DEPLOY_BRANCH
    assert auto["spec"]["update"] == {"path": "./", "strategy": "Setters"}


def test_the_deploy_automation_is_rendered_by_flux():
    resources = yaml.safe_load(
        (ROOT / "platform/image-automation/kustomization.yaml").read_text()
    )["resources"]
    assert "deploy.yaml" in resources


def test_a_push_rebuilds_flux_deploy_at_once():
    (receiver,) = _docs("platform/flux-webhook/receiver.yaml")
    targets = {(r["kind"], r["name"]) for r in receiver["spec"]["resources"]}
    assert ("ImageUpdateAutomation", "deploy") in targets


def test_a_bump_on_flux_deploy_starts_no_workflow():
    assert _workflows_fired_by_push(DEPLOY_BRANCH) == []


def test_ci_still_grades_the_queue_and_main():
    # The scan above must be able to fail: the same reader sees ci.yml fire where it should.
    assert "ci.yml" in _workflows_fired_by_push("queue/b1")
    assert "ci.yml" in _workflows_fired_by_push("main")

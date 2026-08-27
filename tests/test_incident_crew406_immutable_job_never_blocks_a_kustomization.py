"""Incident crew#406 (oke-check 33033770482): idp#296 rolled the sovereign-worker image through the
`images:` transform in platform/temporal/kustomization.yaml, the Job kini-finish-0 carried that
image, a Job's spec.template is immutable, and Flux refused the whole temporal Kustomization:
`Job.batch "kini-finish-0" is invalid: spec.template: Invalid value`.

The rule: every Job under platform/ whose image is rewritten by its kustomization's `images:`
transform declares how Flux should treat drift, `kustomize.toolkit.fluxcd.io/ssa: IfNotPresent`
(create once per name) or `kustomize.toolkit.fluxcd.io/force: Enabled` (recreate). Rung 4.
"""
import pathlib

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLATFORM = ROOT / "platform"
OK = {("kustomize.toolkit.fluxcd.io/ssa", "IfNotPresent"), ("kustomize.toolkit.fluxcd.io/force", "Enabled")}


def _docs(path: pathlib.Path):
    try:
        return [d for d in yaml.safe_load_all(path.read_text()) if isinstance(d, dict)]
    except yaml.YAMLError:
        return []


def transformed_images(kdir: pathlib.Path) -> set[str]:
    k = kdir / "kustomization.yaml"
    if not k.is_file():
        return set()
    return {i.get("name") for d in _docs(k) for i in (d.get("images") or []) if i.get("name")}


def unguarded_jobs(platform: pathlib.Path = PLATFORM) -> list[str]:
    """Jobs whose image the transform rewrites and that say nothing about immutability."""
    bad = []
    for path in sorted(platform.rglob("*.yaml")):
        images = transformed_images(path.parent)
        if not images:
            continue
        for d in _docs(path):
            if d.get("kind") != "Job":
                continue
            containers = (d.get("spec") or {}).get("template", {}).get("spec", {}).get("containers", [])
            if not any(str(c.get("image", "")).split(":")[0] in images for c in containers):
                continue
            ann = ((d.get("metadata") or {}).get("annotations") or {})
            if not any((k, v) in OK for k, v in ann.items()):
                bad.append(f"{path.relative_to(platform)}:{d['metadata'].get('name')}")
    return bad


def test_every_transformed_job_declares_its_drift_policy():
    assert unguarded_jobs() == []


def test_the_rule_refuses_the_incident_shape(tmp_path):
    (tmp_path / "kustomization.yaml").write_text("images:\n- name: idp/sovereign-worker\n  newTag: x\n")
    job = "apiVersion: batch/v1\nkind: Job\nmetadata:\n  name: kini-finish-0\n%s\nspec:\n  template:\n    spec:\n      containers:\n      - image: idp/sovereign-worker:local\n"
    (tmp_path / "job.yaml").write_text(job % "")
    assert unguarded_jobs(tmp_path) == ["job.yaml:kini-finish-0"]
    (tmp_path / "job.yaml").write_text(job % "  annotations: {kustomize.toolkit.fluxcd.io/ssa: IfNotPresent}")
    assert unguarded_jobs(tmp_path) == []


@pytest.mark.parametrize("name", ["kini-finish.yaml"])
def test_kini_finish_is_created_once_per_name(name):
    d = next(x for x in _docs(PLATFORM / "temporal" / name) if x.get("kind") == "Job")
    assert d["metadata"]["annotations"]["kustomize.toolkit.fluxcd.io/ssa"] == "IfNotPresent"

"""Incident 2026-08-28 (crew#539): `robusta/robusta` sat Ready=False for 8h with
`admission webhook "validate.kyverno.svc-fail" denied the request` on Deployment/robusta-runner,
and Flux could not remediate it (`missing target release for rollback`), which held
`monitoring` and `monitoring-rules` down behind it.

Two defects, one incident.

The manifest: chart robusta 0.48.0 marks three secret references `optional: true`, and
`no-optional-secret-references` -- the 2026-08-24 incident written as a rule -- refuses every one.
Nothing here is excused: the two secrets the chart itself renders are declared required, and the
third (`robusta-auth-config-secret`, which nothing in this estate creates -- the Robusta UI is off)
stops being a secret reference at all and becomes the empty directory the kubelet was mounting for
it anyway.

The judge: `bin/idp-kyverno-render` falls back to the pinned upstream library when prospector's
checkout is absent, and CI never had that checkout. So CI judged 24 of 26 policies -- missing
exactly the two this estate wrote from its own incidents -- and printed `render clean` for the
Deployment admission then refused. Rule (rung 4): the judge is BLIND, never a pass, when the
estate-only policies are not in the set, and CI checks them out so it is not blind.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
ESTATE_ONLY = ("no-optional-secret-references", "money-rail-single-writer")


def _kustomize(tmp_path: Path, resource: Path, patches: list) -> list:
    (tmp_path / "runner.yaml").write_text(resource.read_text())
    (tmp_path / "kustomization.yaml").write_text(yaml.safe_dump(
        {"apiVersion": "kustomize.config.k8s.io/v1beta1", "kind": "Kustomization",
         "resources": ["runner.yaml"], "patches": patches}))
    out = subprocess.run(["kubectl", "kustomize", str(tmp_path)],
                         capture_output=True, text=True, check=True).stdout
    return [d for d in yaml.safe_load_all(out) if d]


def _runner_patches() -> list:
    docs = [d for d in yaml.safe_load_all((ROOT / "platform/robusta/robusta.yaml").read_text()) if d]
    hr = next(d for d in docs if d["kind"] == "HelmRelease")
    return [p for pr in hr["spec"]["postRenderers"] for p in pr["kustomize"]["patches"]
            if p["target"].get("name") == "robusta-runner"]


@pytest.mark.skipif(not shutil.which("kubectl"), reason="kubectl builds the postRenderer patch")
def test_the_postrenderer_leaves_no_optional_secret_reference(tmp_path: Path) -> None:
    """The chart's three `optional: true` references, put through the release's own patches."""
    fixture = ROOT / "tests/fixtures/kyverno/robusta-chart/runner.yaml"
    assert "optional: true" in fixture.read_text(), "the fixture must still carry what we fix"
    dep = _kustomize(tmp_path, fixture, _runner_patches())[0]
    spec = dep["spec"]["template"]["spec"]

    assert spec["containers"][0]["envFrom"] == [{"secretRef": {"name": "robusta-runner-secret"}}]
    vols = {v["name"]: v for v in spec["volumes"]}
    assert vols["playbooks-config-secret"]["secret"] == {"secretName": "robusta-playbooks-config-secret"}
    # Nothing creates robusta-auth-config-secret, so requiring it would deadlock the pod; the
    # kubelet already mounts an empty directory there and an emptyDir mounts the same one.
    assert vols["auth-config-secret"] == {"name": "auth-config-secret", "emptyDir": {}}
    assert "optional" not in yaml.safe_dump(dep)


@pytest.mark.skipif(not shutil.which("kubectl"), reason="kubectl builds the postRenderer patch")
def test_the_auth_directory_is_still_mounted(tmp_path: Path) -> None:
    """LAW 38 control: the fix must not remove a path the runner reads."""
    dep = _kustomize(tmp_path, ROOT / "tests/fixtures/kyverno/robusta-chart/runner.yaml", _runner_patches())[0]
    mounts = dep["spec"]["template"]["spec"]["containers"][0]["volumeMounts"]
    assert {"name": "auth-config-secret", "mountPath": "/etc/robusta/auth"} in mounts


@pytest.mark.skipif(not (shutil.which("kyverno") and shutil.which("helm") and shutil.which("kubectl")),
                    reason="the judge needs helm, kubectl and the kyverno CLI")
def test_the_judge_is_blind_not_green_without_the_estate_policies(tmp_path: Path) -> None:
    """The defect itself: with only the upstream library the judge used to print `render clean`."""
    env = {**os.environ, "IDP_KYVERNO_POLICIES": str(tmp_path / "absent")}
    r = subprocess.run([str(ROOT / "bin/idp-kyverno-render"), "platform/robusta"],
                       cwd=ROOT, capture_output=True, text=True, env=env)
    assert r.returncode == 2, f"a partial policy set must be BLIND, got rc={r.returncode}\n{r.stdout}"
    assert "BLIND  policies" in r.stdout, r.stdout + r.stderr
    assert ESTATE_ONLY[0] in r.stdout
    assert "ok    render" not in r.stdout, "nothing may be graded once the set is known short"


def test_ci_checks_the_estate_policies_out_for_every_job_that_judges() -> None:
    """And the reason it was blind for months: no job ever had prospector's policies."""
    wf = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    judging = [name for name, job in wf["jobs"].items()
               if any("bin/idp-ci" in str(s.get("run", "")) or "pytest tests" in str(s.get("run", ""))
                      for s in job.get("steps", []))]
    assert judging, "no job runs the judge at all"
    for name in judging:
        steps = wf["jobs"][name]["steps"]
        checkouts = [s.get("with", {}).get("repository") for s in steps if "checkout" in str(s.get("uses", ""))]
        assert "chidionyema/prospector" in checkouts, f"job {name} judges with no estate policies"
        env = [s.get("env", {}).get("IDP_KYVERNO_POLICIES") for s in steps if s.get("env")]
        assert any(e and ".kyverno-policies/deploy/k8s/policies" in e for e in env), \
            f"job {name} checks the policies out and never points the judge at them"


def test_the_guard_names_both_estate_policies() -> None:
    """A third estate-only policy added later must be added here too, or it is judged by nobody."""
    guard = (ROOT / "bin/idp-kyverno-render").read_text()
    for want in ESTATE_ONLY:
        assert want in guard, f"{want} is not in the BLIND check"

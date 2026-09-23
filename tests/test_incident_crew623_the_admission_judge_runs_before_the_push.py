"""The cluster's own admission rules are read before a push, and over every directory.

Founder, 2026-08-29, on the money layer arriving as a red pull request: "why did you not
investigate cluster before starting", and then "no good reason is unacceptable as answer".

The reason was mechanical and it was two holes, both measured on this branch:

  1. `bin/idp-kyverno-render` renders a HelmRelease the way helm-controller will and puts the
     cluster's ClusterPolicies over the result, offline, in about half a minute. It was called
     from `bin/idp-ci` and from nowhere else, so nothing on the machine ran it before a push.
     platform/commerce/app went out with 128 admission failures and CI was the first to say so.
  2. `bin/idp-ci` discovered HelmReleases at `platform/*/*.yaml platform/*/*/*.yaml` but plain
     workloads at `platform/*/*.yaml` only. Three directories two levels down were therefore
     judged by nothing at all: platform/backstage/base (the portal), platform/oci/autoscaler,
     and platform/commerce/data -- the money layer's own database and cache.

Both are closed by one script, `bin/idp-kyverno-dirs`, which owns the list of judged directories
so there is one copy of it, and by a rung in .githooks/pre-push. This file is the guard: it fails
if either hole reopens.
"""

import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DIRS = ROOT / "bin" / "idp-kyverno-dirs"
CI = ROOT / "bin" / "idp-ci"
HOOK = ROOT / ".githooks" / "pre-push"
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "HelmRelease"}


def _judged():
    r = subprocess.run([str(DIRS)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return set(r.stdout.split())


def _ships_a_workload(directory: Path):
    for f in directory.glob("*.yaml"):
        if f.name == "kustomization.yaml":
            continue
        try:
            docs = list(yaml.safe_load_all(f.read_text()))
        except yaml.YAMLError:
            continue
        if any(d and d.get("kind") in WORKLOADS for d in docs):
            return True
    return False


def test_every_directory_that_ships_a_workload_is_judged():
    """Computed here by walking the tree, not by reading the script's own globs.

    A guard that asks the script under test what it thinks it covers proves nothing.
    """
    expected = {
        str(d.relative_to(ROOT))
        for d in ROOT.glob("platform/*/")
        if (d / "kustomization.yaml").exists() and _ships_a_workload(d)
    } | {
        str(d.relative_to(ROOT))
        for d in ROOT.glob("platform/*/*/")
        if (d / "kustomization.yaml").exists() and _ships_a_workload(d)
    }
    missing = expected - _judged()
    assert not missing, (
        f"directories the admission judge would never see: {sorted(missing)}"
    )


def test_the_three_directories_the_old_globs_missed_are_in_the_list():
    """The incident itself, by name. The sweep above would pass if all three were deleted."""
    judged = _judged()
    for d in (
        "platform/backstage/base",
        "platform/oci/autoscaler",
        "platform/commerce/data",
    ):
        assert d in judged, (
            f"{d} is judged by nothing; this is the crew#623 hole reopened"
        )


def test_the_ci_rung_asks_this_script_rather_than_carrying_its_own_globs():
    """Two copies of the discovery is how the two globs came to disagree in the first place."""
    body = CI.read_text()
    assert "bin/idp-kyverno-dirs" in body, (
        "bin/idp-ci no longer asks the one owner of the list"
    )
    stray = [
        line
        for line in body.splitlines()
        if "grep -lE '^kind: HelmRelease" in line
        or "kind: (Deployment|StatefulSet" in line
    ]
    assert not stray, f"bin/idp-ci grew a second copy of the discovery: {stray}"


def test_the_pre_push_hook_runs_the_judge():
    """The rung that would have caught the money layer in half a minute instead of in CI."""
    body = HOOK.read_text()
    assert "bin/idp-kyverno-render" in body, (
        "nothing local renders the charts against the cluster's policies; a chart that admission "
        "refuses can be pushed again and CI will be the first to know"
    )
    assert "bin/idp-kyverno-dirs" in body, (
        "the hook judges an unscoped list, so it is slow enough to be removed"
    )


def test_a_machine_without_helm_is_warned_and_not_refused():
    """LAW 38: a fence a correct machine cannot satisfy is an outage, not a fence.

    bin/idp-kyverno-render exits 2 when helm, kubectl or kyverno is absent. The hook must say so
    and let the push through -- CI still judges -- and must still refuse a real failure.
    """
    body = HOOK.read_text()
    rung = body[body.index("kyv_base=") : body.index("shared=")]
    assert re.search(r"2\)\s*echo \"BLIND", rung), (
        "exit 2 (no CLI installed) does not warn"
    )
    assert "exit 1" in rung.split("*)", 1)[1], "a refused render does not stop the push"
    assert "exit 1" not in rung.split("*)", 1)[0], "the BLIND path refuses the push"

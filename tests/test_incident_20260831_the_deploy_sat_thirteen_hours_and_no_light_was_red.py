"""Incident, 2026-08-31: catalogue.mumchimp.com served an image built thirteen hours earlier and
every light in the estate was green.

Shipping here is a pull request. image-automation-controller writes the new tag onto
`flux/image-updates`; image-update-pr.yml opens the pull request that carries it to main; nothing
reaches the cluster until that pull request merges. It merged itself on GitHub's native auto-merge
until `allow_auto_merge` was turned off on the repository on 2026-08-30 -- by hand, in the web user
interface, and in no file in this estate (`git log -S founder-only-releases` finds nothing). From
then on `gh pr merge --auto` answered `enablePullRequestAutoMerge` and the step exited 1, on a
branch nobody reads.

WHY NOTHING WENT RED, which is the part worth guarding. Every green light measured something else:
`ci` grades the build, `build-multiarch` grades the image, `login-drill` signs in to the portal and
the *old* portal signs in fine. Nothing anywhere compared what is running to what was built. That
comparison did not exist, so its absence could not be red -- the estate's `silent-green` class.

Three faults had to line up, and all three are held here:
  1. the robots asked GitHub for an auto-merge the repository refuses
     -> tests/test_incident_20260831_the_deploy_robot_asked_for_a_merge_the_repo_refuses.py
  2. nothing landed the deploy once auto-merge was gone -> .github/workflows/deploy-when-green.yml,
     and it may land without the founder only because bin/idp-image-only-diff PROVES the pull
     request is nothing but automation-owned tag lines (founder, 2026-08-31: shipping code he
     already approved when he merged it is not a second release)
  3. bin/idp-pr-age drafted the deploy pull request at the 4h bound and would have closed it at 24
     -> tests/test_incident_crew607_cp2_cp3_a_green_pr_merges_itself.py
And the missing instrument is bin/idp-deploy-lag, which grades main against the deploy branch.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import subprocess

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github/workflows/deploy-when-green.yml"
ONLY = ROOT / "bin/idp-image-only-diff"
LANDABLE = ROOT / "bin/idp-pr-landable"

TAG = (
    "newTag: main-3063-ca2a0d316f327861f1e2877aced4e489e77f7160 "
    '# {"$imagepolicy": "flux-system:backstage:tag"}'
)
OLD = (
    "newTag: main-2913-2ca4dd3312e0e28516a0bd4b1a6b8f0e1f6b2c7d "
    '# {"$imagepolicy": "flux-system:backstage:tag"}'
)


def _load(path, name):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def _diff(*changes, header="clusters/oke/backstage.yaml"):
    out = [
        f"diff --git a/{header} b/{header}",
        "index 1111111..2222222 100644",
        f"--- a/{header}",
        f"+++ b/{header}",
        "@@ -30,7 +30,7 @@",
    ]
    out.extend(changes)
    return "\n".join(out) + "\n"


# ---- the gate that makes an unattended deploy safe -------------------------------------------


def test_a_pure_tag_bump_is_allowed():
    mod = _load(ONLY, "image_only")
    ok, why = mod.grade(_diff("   name: backstage", f"-  {OLD}", f"+  {TAG}"))
    assert ok is True, why
    assert "1 image tag line" in why


def test_a_new_or_deleted_file_is_refused():
    mod = _load(ONLY, "image_only")
    d = _diff(f"-  {OLD}", f"+  {TAG}").replace(
        "index 1111111..2222222 100644", "new file mode 100644"
    )
    assert mod.grade(d)[0] is False
    d = _diff(f"-  {OLD}", f"+  {TAG}").replace(
        "index 1111111..2222222 100644", "deleted file mode 100644"
    )
    assert mod.grade(d)[0] is False


def test_a_tag_line_that_carries_no_imagepolicy_marker_is_refused():
    """The marker is what says the controller owns the line. A hand-written newTag: is a person
    changing what runs, which is exactly the change that waits for the founder."""
    mod = _load(ONLY, "image_only")
    ok, why = mod.grade(_diff("-  newTag: main-2913", "+  newTag: something-i-typed"))
    assert ok is False, why


def test_moving_a_line_to_a_different_policy_is_refused():
    mod = _load(ONLY, "image_only")
    other = TAG.replace("flux-system:backstage:tag", "flux-system:prospector:tag")
    ok, why = mod.grade(_diff(f"-  {OLD}", f"+  {other}"))
    assert ok is False and "policy" in why, why


def test_an_empty_diff_is_blind_and_never_a_pass():
    """`gh pr diff` answering nothing is a failure to measure. The estate's silent-green class is
    exactly a check that reads an empty answer as an empty problem."""
    mod = _load(ONLY, "image_only")
    ok, why = mod.grade("")
    assert ok is None, why


def test_the_tool_exits_one_on_a_refusal_and_two_when_blind(tmp_path):
    """The workflow branches on the exit code, so the codes are the contract."""
    mod = _load(ONLY, "image_only")
    good = tmp_path / "good.diff"
    good.write_text(_diff(f"-  {OLD}", f"+  {TAG}"))
    bad = tmp_path / "bad.diff"
    bad.write_text(_diff(f"-  {OLD}", f"+  {TAG}", "+  replicas: 3"))
    empty = tmp_path / "empty.diff"
    empty.write_text("")
    assert mod.main(["--diff", str(good)]) == 0
    assert mod.main(["--diff", str(bad)]) == 1
    assert mod.main(["--diff", str(empty)]) == 2


# ---- is it finished? -------------------------------------------------------------------------


def _pr(**kw):
    pr = {
        "isDraft": False,
        "mergeStateStatus": "CLEAN",
        "labels": [],
        "statusCheckRollup": [
            {"name": c, "status": "COMPLETED", "conclusion": "SUCCESS"}
            for c in sorted(REQUIRED)
        ],
    }
    pr.update(kw)
    return pr


LAND = _load(LANDABLE, "pr_landable")
REQUIRED = LAND.required_contexts()


def test_the_required_contexts_come_from_the_ruleset_file_not_a_list_in_the_tool():
    """crew#105: PR #111 merged unreviewed because review-gate was not yet on main, so its check
    never appeared and "not failing" read as green. A required check added to the ruleset and not
    to this tool would be the same hole, so the tool reads the ruleset."""
    assert REQUIRED, "no required contexts were read; the ruleset path is wrong"
    assert "bdd" in REQUIRED and "security-scan" in REQUIRED, sorted(REQUIRED)


def test_a_green_clean_deploy_lands():
    assert LAND.verdict(_pr(), REQUIRED)[0] == "MERGE"


def test_a_required_check_that_never_ran_is_not_green():
    one = sorted(REQUIRED)[0]
    pr = _pr()
    pr["statusCheckRollup"] = [c for c in pr["statusCheckRollup"] if c["name"] != one]
    v, why = LAND.verdict(pr, REQUIRED)
    assert v == "SKIP" and one in why, why


def test_nothing_lands_while_a_check_is_still_running():
    pr = _pr()
    pr["statusCheckRollup"][0] = dict(
        pr["statusCheckRollup"][0], status="IN_PROGRESS", conclusion=None
    )
    assert LAND.verdict(pr, REQUIRED)[0] == "SKIP"


def test_a_failing_check_never_lands():
    pr = _pr()
    pr["statusCheckRollup"][0] = dict(pr["statusCheckRollup"][0], conclusion="FAILURE")
    v, why = LAND.verdict(pr, REQUIRED)
    assert v == "SKIP" and "failing" in why, why


def test_a_draft_a_hold_label_and_a_conflict_each_stop_it():
    assert LAND.verdict(_pr(isDraft=True), REQUIRED)[0] == "SKIP"
    assert LAND.verdict(_pr(labels=[{"name": "do-not-merge"}]), REQUIRED)[0] == "SKIP"
    assert LAND.verdict(_pr(mergeStateStatus="DIRTY"), REQUIRED)[0] == "SKIP"


def test_behind_main_is_refreshed_rather_than_skipped():
    """crew's two stalled pull requests became conflicts because BEHIND was treated as a wait."""
    assert LAND.verdict(_pr(mergeStateStatus="BEHIND"), REQUIRED)[0] == "UPDATE"


def test_a_pull_request_with_no_checks_is_unproven_not_green():
    assert LAND.verdict(_pr(statusCheckRollup=[]), REQUIRED)[0] == "SKIP"


def test_the_tool_always_exits_zero(tmp_path):
    """A verdict of "not yet" is a normal answer, and a red run for it would train the estate to
    ignore this lane."""
    import json

    f = tmp_path / "pr.json"
    f.write_text(json.dumps(_pr(isDraft=True)))
    assert LAND.main([str(f)]) == 0
    assert LAND.main([str(tmp_path / "does-not-exist.json")]) == 0


# ---- the lane --------------------------------------------------------------------------------


def _wf():
    return yaml.safe_load(WF.read_text())


def test_the_lane_does_not_depend_on_a_cron_firing():
    """GitHub drops scheduled runs: a */5 cron in this estate fired 10 times in 60 hours. The cron
    here is a backstop and the workflow_run triggers are the mechanism."""
    on = _wf()[True] if True in _wf() else _wf()["on"]
    assert "workflow_run" in on and "ci" in on["workflow_run"]["workflows"]
    assert "workflow_dispatch" in on, "a person must be able to run the deploy by hand"


def test_one_deploy_at_a_time():
    assert _wf()["concurrency"]["group"] == "deploy-when-green"
    assert _wf()["concurrency"]["cancel-in-progress"] is False, (
        "cancelling a deploy mid-merge is how a half-landed tag happens"
    )


# ---- and the instrument that would have said so ------------------------------------------------


def test_the_deploy_lag_instrument_exists_and_runs():
    """The thirteen hours were silent because nothing compared what runs to what was built."""
    lag = ROOT / "bin/idp-deploy-lag"
    assert lag.exists() and lag.stat().st_mode & 0o111, (
        "bin/idp-deploy-lag must be executable"
    )
    p = subprocess.run([str(lag), "--help"], capture_output=True, text=True, timeout=30)
    assert p.returncode == 0, p.stderr

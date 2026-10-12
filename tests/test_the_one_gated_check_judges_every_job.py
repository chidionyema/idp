"""`ci-success` is the one check the ruleset requires of this workflow, so a job it does not
judge grades nothing (2026-10-12).

Measured, not reasoned: on main's a66f09e0b (PR #5792, 2026-10-11T18:27:56Z) `security-scan`
concluded `failure` and `ci-success` concluded `success` -- same commit, same run. The estate
landed that commit with a red secret scan. `ci-success` held a hand-written `needs:` list and a
hand-written `for job in ...` loop, and `security-scan` was in neither of them, so the scan's
verdict could not reach the check the ruleset requires. The job's own action description said
"Non-zero exit fails the job; the ruleset `estate-security-scan` then refuses the merge" -- that
ruleset does not exist on idp, and nothing refused.

These tests pin the wiring, not the scan. A job is judged when `ci-success` names it in the loop
it fails on, or when a judged job reads that job's verdict by name (`needs.<job>.result`) -- the
mechanism `bdd` uses to speak for `bdd-suites`. Every other job in ci.yml must be named in
`EXEMPT` with a reason, so the next job added outside the gate fails this file instead of failing
silently in production. `EXEMPT` records known omissions, not blessings: each entry states what a
red verdict there refuses today, and for four of the five the honest answer is nothing.

This test found its own case on the way in: `bdd-suites` is judged through `bdd` (which reads
`needs.bdd-suites.result`), not directly, and a naive "is it in needs?" reading calls it an
omission. Both directions matter -- see the last test for the reverse, where a red `verifier` is
masked rather than judged.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

# Jobs in ci.yml that `ci-success` does not judge, directly or through another job's verdict.
# Each reason says what a red verdict here refuses today; for four of the five that is nothing.
EXEMPT = {
    "verifier": (
        "runs verifier.yml on every pull request. Not in ci-success's needs, not one of the eight "
        "contexts the ruleset requires on main (read 2026-10-12: bdd, ci-success, "
        "fast-gate / fast-gate, guarded-paths, test, portal-app, executes-gate, "
        "feature-request-plan), and no judged job reads its verdict. It is also masked, not just "
        "unenforced: bdd-suites needs verifier and skips when it fails, and bdd passes a skipped "
        "bdd-suites (its own comment, 2026-09-04), so a red verifier reaches ci-success as green."
    ),
    "offline-gate": (
        "runs bin/idp-ci on the push to main and the merge queue. Same position as verifier: not "
        "judged, not required by name, read by nothing. Wiring it would also make ci-success wait "
        "on this job's ~586s on every push (its own comment, 2026-09-04), a timing trade this "
        "change does not take."
    ),
    "messaging-demo": (
        "runs the messaging demos on the push to main and the merge queue. Same position: not "
        "judged by ci-success, not required by name, read by nothing."
    ),
    "migrate-domain": (
        "runs the domain-migration tool check on the push to main and the merge queue. Same "
        "position: not judged by ci-success, not required by name, read by nothing."
    ),
    "estate-graph-sync": (
        "a notification, not a gate: its dispatch step carries `continue-on-error: true` and it "
        "runs on the push to main only."
    ),
}


def _jobs():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]


def _runner_text(job):
    return "\n".join(step.get("run") or "" for step in job.get("steps", []))


def _needs_of(job):
    """`needs:` is a list or a single job name in this workflow (`bdd: needs: bdd-suites`);
    reading only the list form silently skips the scalar one."""
    needs = job.get("needs")
    if needs is None:
        return []
    return [needs] if isinstance(needs, str) else [str(n) for n in needs]


def _judged_in_loop():
    """The jobs ci-success fails on, read off its own `for job in ...` loop."""
    for step in _jobs()["ci-success"].get("steps", []):
        match = re.search(r"for job in ([^;]+); do", step.get("run") or "")
        if match:
            return match.group(1).split()
    raise AssertionError(
        "ci-success no longer contains a `for job in ...; do` loop, so this test cannot tell "
        "which jobs it fails on -- and neither could a reader"
    )


def _judged():
    """Every job whose verdict reaches `ci-success`: the loop, plus any job some judged job
    reads by name. Measured from the workflow's own text, so a job counts only when the runner
    would actually look at its result."""
    jobs = _jobs()
    judged = set(_judged_in_loop())
    changed = True
    while changed:
        changed = False
        for name in sorted(judged):
            for dep in _needs_of(jobs[name]):
                if dep in judged:
                    continue
                text = _runner_text(jobs[name])
                read = re.search(
                    rf"needs\.{re.escape(dep)}\.result", text
                ) or re.search(rf"needs\[['\"]{re.escape(dep)}['\"]\]", text)
                if read:
                    judged.add(dep)
                    changed = True
    return judged


def test_the_secret_scan_reaches_the_one_gated_check():
    """The regression. On main's a66f09e0b this was false and the gate said green."""
    assert "security-scan" in _judged(), (
        "security-scan must be judged by ci-success: it is the estate's answer to 'a leak in git "
        "history blocks the merge', and ci-success is the check the ruleset requires. Outside it, "
        "the job can be as red as it likes (measured red on a66f09e0b) and nothing refuses."
    )


def test_the_needs_list_and_the_loop_that_reads_it_agree():
    """`needs:` decides what the job may read; the loop decides what it fails on. Drift between
    them is silence: a job in `needs` but not in the loop is waited for and then ignored."""
    needs = _jobs()["ci-success"].get("needs")
    assert isinstance(needs, list), (
        "ci-success's `needs` is no longer a list this test can read, so the gate's coverage can "
        "no longer be measured -- which is the failure this file exists to prevent"
    )
    assert set(str(n) for n in needs) == set(_judged_in_loop())


def test_no_job_that_can_fail_is_left_outside_the_gate():
    unjudged = set(_jobs()) - {"ci-success"} - _judged() - set(EXEMPT)
    assert not unjudged, (
        f"jobs that can fail and are judged by nothing: {sorted(unjudged)}. Add each to "
        "ci-success's `needs:` and to the `for job in ...` loop (or have a judged job read its "
        "verdict), or name it in EXEMPT here with the reason its red verdict may be ignored."
    )


def test_the_exemptions_are_live_and_still_exempt():
    """An exemption for a job that no longer exists, or is now judged, is a stale claim about
    coverage -- it would hide a later removal of the judgement."""
    stale = (set(EXEMPT) - set(_jobs())) | (set(EXEMPT) & _judged())
    assert not stale, (
        f"EXEMPT names jobs that do not exist or are already judged by ci-success: "
        f"{sorted(stale)}; remove them from EXEMPT"
    )


def test_a_pull_request_skips_the_scan_and_a_skip_is_still_a_pass():
    """The two facts the wiring rests on. The scan runs on the push to main and the merge queue,
    not on a pull request, so on a PR it is `skipped` -- and `skipped` must stay a pass in the
    loop, exactly as it is for the `bdd` leg, or every pull request would be refused for a scan
    it was never allowed to run."""
    assert _jobs()["security-scan"].get("if") == "github.event_name != 'pull_request'"
    loop_run = next(
        step.get("run") or ""
        for step in _jobs()["ci-success"].get("steps", [])
        if "for job in" in (step.get("run") or "")
    )
    assert "success|skipped)" in loop_run.replace(" ", ""), (
        "ci-success no longer treats `skipped` as a pass, so a pull request -- where the scan is "
        "skipped by construction -- would now be refused by it"
    )


def test_a_dependency_counts_only_when_a_judged_job_reads_its_result_by_name():
    """Both directions of the mechanism, because they look identical from outside and are
    opposite in effect.

    Judged: `bdd-suites` is never named in ci-success's loop, and it is judged anyway -- `bdd` is
    in the loop and reads `needs.bdd-suites.result`, so a red suite set is a red gate.

    Not judged: `verifier` is likewise reachable and is *masked* -- bdd-suites needs it, a failed
    verifier skips the suites, and bdd passes a skipped suite by its own rule. The verdict is
    dropped at that hand-off, which is why `verifier` stays in EXEMPT and why adding it to
    ci-success's needs would change nothing on its own."""
    judged = _judged()
    assert "bdd-suites" in judged and "bdd-suites" not in _judged_in_loop()
    assert "needs.bdd-suites.result" in _runner_text(_jobs()["bdd"])

    assert "verifier" not in judged, (
        "if verifier has become judged, remove it from EXEMPT and say what changed -- today its "
        "red verdict is dropped by bdd's skip-is-a-pass rule, not carried to the gate"
    )
    assert "verifier" in _needs_of(_jobs()["bdd-suites"])

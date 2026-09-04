"""crew#584, 2026-08-28: ci.yml's bdd job ran the acceptance suite (54 s) and the root pytest
suite (57 s) one after the other on a single runner -- 2m13s on run 33203670180 -- when the
platform's own matrix runs them side by side. The fix is GitHub's matrix, not a script: the job
keeps its id, each suite step is gated on its own matrix leg, and the wall-clock is the slower
suite plus setup instead of the sum.

The guard: the bdd job declares a matrix with both legs, every pytest step is gated on exactly one
leg, and the two legs each own at least one pytest step -- so nobody can quietly collapse it back
into one serial job, or gate both suites onto the same leg (which is the serial job with extra
runner time).
"""

from pathlib import Path

import yaml

WF = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"


def _bdd():
    return yaml.safe_load(WF.read_text())["jobs"]["bdd-suites"]


def test_the_bdd_job_is_a_matrix_of_both_suites():
    job = _bdd()
    legs = job["strategy"]["matrix"]["suite"]
    assert sorted(legs) == ["acceptance", "tests"], legs
    assert job["strategy"]["fail-fast"] is False, (
        "one red suite must not cancel the other's verdict"
    )


# 2026-08-29, the second half of this incident. Splitting the suites made GitHub publish the
# checks as `bdd (acceptance)` and `bdd (tests)`, and the merge rule on main waits for a check
# named exactly `bdd`. The pull request was MERGEABLE with every leg green and BLOCKED for 12
# hours on a name no run would report again -- a stall with no red anywhere to read.
#
# REQUIRED is the merge rule's own list. Re-read it with:
#   gh api repos/chidionyema/idp/rules/branches/main \
#     --jq '[.[]|select(.type=="required_status_checks")|.parameters.required_status_checks[].context]|unique'
REQUIRED = {
    "bdd",
    "offline-gate",
    "security-scan",
}


def _ci_jobs():
    return yaml.safe_load(WF.read_text())["jobs"]


def test_the_bdd_gate_reports_for_the_whole_matrix():
    """The stable name still exists, and it is red when a leg is red rather than skipped."""
    gate = _ci_jobs()["bdd"]
    needs = gate["needs"]
    assert "bdd-suites" in ([needs] if isinstance(needs, str) else needs), needs
    assert gate.get("if") and "always()" in str(gate["if"]), (
        "without if: always() a failed leg leaves `bdd` skipped, and the rule waits on it"
    )
    assert any(
        "needs.bdd-suites.result" in (s.get("run") or "") for s in gate["steps"]
    ), gate

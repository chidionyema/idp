"""crew#586 CP5: the daily portal-page PR (bot/conscience-page, idp#640) and state/live-diagram
(idp#635) landed as action_required. GitHub held every run because the repository's
fork-PR approval policy was `first_time_contributors`, and github-actions counts as one.
An auto-merge PR whose checks never start is a daily hand. The policy is now a file
(platform/github/actions-pr-approval.json) and a rung of bin/repo-rulesets, so drift is
reported and --apply repairs it on every repository the estate owns."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "platform/github/actions-pr-approval.json"
SCRIPT = (ROOT / "bin/repo-rulesets").read_text()


def test_the_spec_names_the_one_policy_that_lets_bot_prs_run():
    assert json.loads(SPEC.read_text()) == {"approval_policy": "first_time_contributors_new_to_github"}


def test_repo_rulesets_reads_the_live_policy_and_repairs_it_from_the_spec():
    assert "actions/permissions/fork-pr-contributor-approval" in SCRIPT
    assert re.search(r'gh api -X PUT "/repos/\$OWNER/\$repo/actions/permissions/fork-pr-contributor-approval" --input "\$APPROVAL"', SCRIPT)
    assert 'apply_pr_approval "$repo"' in SCRIPT, "the rung runs for every repository, not only idp"


def test_drift_counts_and_an_unreadable_policy_is_blocked_never_skipped():
    body = SCRIPT[SCRIPT.index("apply_pr_approval() {"):]
    body = body[: body.index("\n}")]
    assert "drift=$((drift+1))" in body
    assert "BLOCKED" in body and "blocked=$((blocked+1))" in body

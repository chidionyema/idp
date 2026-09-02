# Runbook: The merge queue

## Normal operation
Nothing to do. Green pull requests queue themselves via
`gh pr merge <number> --squash --auto` and land without a human.

## A pull request is stuck in the queue
1. Read the queue: `gh api repos/chidionyema/idp/merge-queue/main --jq '.entries[] | {pr: .pull_request.number, state}'` — or open the Pull requests tab and click "Merge queue."
2. A stuck entry almost always means a required check never reported in the
   queued run. Compare the checks on the queue entry with the six required
   contexts in `platform/github/ruleset.idp.required-checks.json`.
3. To eject one entry: `gh pr merge <number> --disable-auto`; fix, re-queue.

## Pause the queue (incident)
Set the ruleset to evaluate-only:
`gh api -X PUT repos/chidionyema/idp/rulesets/<id> --input platform/github/ruleset.idp.merge-queue.json` after editing `"enforcement": "disabled"` in a branch — or, faster in an
emergency, disable it in the repository settings under Rules, then apply the declared state
git afterwards so `bin/repo-rulesets` reads clean.

## Roll the whole thing back
Delete the `idp-merge-queue` ruleset and restore the review requirement by
reverting the commit that introduced these files, then run
`bin/repo-rulesets --apply`. The estate is back to founder-merged pull
requests in one command.

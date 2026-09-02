# Runbook: The merge queue

## Availability, read this first
GitHub refuses the `merge_queue` ruleset rule on this repository because a
person, not an organization, owns it: the API answers
`422 Validation Failed: Invalid rule 'merge_queue'`, and the vendor's release
note of 2023-07-12 scopes the queue to repositories owned by organizations —
public on every plan, private on GitHub Enterprise Cloud. Until the repository moves to an
organization, hands-free landing runs on GitHub's automatic merge: the repository
setting `allow_auto_merge` is on, the review count is zero, and
`gh pr merge <number> --squash --auto` lands a pull request the moment its
required checks pass. The queue ruleset stays declared in
`platform/github/ruleset.idp.merge-queue.json`; the day the repository is
organization-owned, `bin/repo-rulesets --apply` arms it with no other change.

## Normal operation (automatic merge bridge)
Nothing to do. Queue each green pull request with
`gh pr merge <number> --squash --auto`; it merges itself when the required
checks pass. One difference from the true queue: automatic merge does not rebuild
the pull request on the latest main before landing, so the required checks
graded the branch head. The push run on main is the backstop when two pull
requests land close together.

## A pull request will not merge itself
1. `gh pr view <number> --json mergeStateStatus,statusCheckRollup` — a failing
   or missing required check is almost always the reason.
2. `DIRTY` means a conflict with main: rebase the branch and push again
   (automatic merge stays armed across pushes).
3. `BLOCKED` with every check green means a ruleset changed; read
   `bin/repo-rulesets` drift output before touching anything.

## When the queue is armed (organization-owned repository)
1. Read the queue: `gh api repos/chidionyema/idp/merge-queue/main --jq '.entries[] | {pr: .pull_request.number, state}'` — or open the Pull requests tab and click "Merge queue."
2. A stuck entry almost always means a required check never reported in the
   queued run. Compare the checks on the queue entry with the six required
   contexts in `platform/github/ruleset.idp.required-checks.json`.
3. To eject one entry: `gh pr merge <number> --disable-auto`; fix, re-queue.

## Pause it (incident)
Automatic merge bridge: `gh api -X PATCH /repos/chidionyema/idp -F allow_auto_merge=false`
holds every new landing; queued green pull requests then wait for a human merge.
Armed queue: set the ruleset to evaluate-only under Rules in the repository
settings, then apply the declared state from git afterwards so
`bin/repo-rulesets` reads clean.

## Roll the whole thing back
Delete the `idp-merge-queue` ruleset record, restore the review requirement by
reverting the commit that introduced these files, run `bin/repo-rulesets --apply`,
and turn `allow_auto_merge` off with the PATCH above. The estate is back to
founder-merged pull requests in two commands.

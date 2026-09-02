# Working with the merge queue

The repository merges its own pull requests. Your job ends at green.

- **What you do:** push the branch, open the pull request, fix anything red,
  then queue it: `gh pr merge <number> --squash --auto`. Done.
- **What the machine does:** lands the pull request squash-merged with the
  branch deleted the moment every required check passes, with zero reviews
  required. On an organization-owned repository the armed queue additionally
  rebuilds your change on top of the latest main and reruns the required
  checks against that exact merged state before landing it.
- **What the founder does:** nothing, unless something fails. The founder
  handles exceptions — a check that will not go green, a drift alert — and
  never green-lights routine merges.
- **When the landing says no:** read
  `gh pr view <number> --json mergeStateStatus,statusCheckRollup`, fix the red
  check or rebase a `DIRTY` branch, push, and the armed automatic merge fires by
  itself.

The queue's declared settings live in git at
`platform/github/ruleset.idp.merge-queue.json`; `bin/repo-rulesets --apply`
is the only way they change. The availability note and the bridge live in
`docs/runbooks/merge-queue.md`.

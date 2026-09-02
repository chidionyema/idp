# Working with the merge queue

The repository merges its own pull requests. Your job ends at green.

- **What you do:** push the branch, open the pull request, fix anything red,
  then queue it: `gh pr merge <number> --squash --auto`. Done.
- **What the machine does:** the queue builds your change on top of the latest
  main, reruns the required checks against that exact merged state, and lands
  it squash-merged with the branch deleted. If several pull requests are
  queued it tests them together and lands them in order.
- **What the founder does:** nothing, unless something fails. The founder
  handles exceptions — a queue entry that cannot rebase, a drift alert — and
  never green-lights routine merges.
- **When the queue says no:** your entry is removed and the pull request gets
  a comment saying which check failed in the queued state. Fix, push, queue
  again.

The queue's own settings live in git at
`platform/github/ruleset.idp.merge-queue.json`; `bin/repo-rulesets --apply`
is the only way they change.

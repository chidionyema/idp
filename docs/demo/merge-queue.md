# The merge queue in two minutes

Open a pull request, get the checks green, and walk away — it merges itself.
That is the whole demo.

1. Push a branch and open a pull request against main.
2. Queue it at any point: `gh pr merge <number> --squash --auto`.
3. Watch it land squash-merged, branch deleted, the moment the required checks
   pass. Nobody types a merge command and nobody green-lights a routine merge.

Today this runs on GitHub's automatic merge, because GitHub offers the true queue only
to repositories owned by an organization (the runbook holds the vendor quote
and the exact refusal). The command above stays the same on the day the
repository moves to an organization — the queue then also rebuilds each pull
request on the latest main and retests it before landing, closing the gap where
two pull requests land close together.

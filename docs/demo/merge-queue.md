# The merge queue in two minutes

Open a pull request, get the checks green, and walk away — the queue merges it
for you. That is the whole demo.

1. Push a branch and open a pull request against main.
2. When the checks turn green, add it to the queue: `gh pr merge <number> --squash --auto`.
3. Watch the queue rebuild it on top of the latest main, run every required
   check once more, and merge it. Nobody types a merge command and nobody
   resolves a moved-main conflict by hand.

If main moved while the pull request waited, the queue rebases and retests
automatically. If that retest fails, the pull request drops out of the queue
and its author is told — that is the only moment a person gets involved.

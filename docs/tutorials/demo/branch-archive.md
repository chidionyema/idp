# Demo: branch archive

## What you see

Open the Actions tab of the repository, choose **branch-archive** and press **Run workflow**
with mode `preview`. The run summary prints a plan and changes nothing:

```
branch-archive  would archive 189 branch(es); kept 6
  would archive: 5 every patch is on main
  would archive: 3 named as a backup
  would archive: 181 unmerged and untouched
  kept: 4 open pull request
  kept: 2 protected
  feat/old-idea -> archive/feat/old-idea (1a2b3c4; 7 patch(es) not on main, untouched 31 days)
  ...
  restore any of them: git push origin refs/tags/archive/<branch>:refs/heads/<branch>
```

Every Monday at 03:41 UTC the same job runs with `--apply`: the tags are pushed in one push,
the branches deleted in one push, and the plan lands on the run summary as the receipt. A
second run over the same repository plans nothing, so the job is idempotent.

## Why it exists

Founder, 2026-09-09: "if branches have been merged into main then they should be deleted, we
need better cleanup mechanism without risk of losing work and all this constant admin and
stress." GitHub already deletes a merged pull request's branch. What piled up was 184 branches
of abandoned work, and every earlier sweep parked them under `backup/<date>/`, which is a branch
list that only grows. A tag keeps every commit reachable and takes nothing from the list a
person reads, so archiving is the zero-loss shape of deletion.

## Bring one back

```
git push origin refs/tags/archive/<branch>:refs/heads/<branch>
```

The branch reappears at the exact tip it had. The tag stays, so the archive is also a record.

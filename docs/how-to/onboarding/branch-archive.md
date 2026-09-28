# Onboarding: branch archive

## What it is

`bin/idp-branch-archive` is the one mechanism that removes branches from the repository.
GitHub's delete-branch-on-merge handles a merged pull request's head; this handles everything
else. A branch is archived when one of three things is true:

| Condition | Why it is safe |
|---|---|
| `git cherry origin/main <branch>` shows no `+` line | every patch is already on main |
| the name starts with `backup/` or `rescue/` | it was parked by an earlier sweep and is already a copy |
| its tip is older than `--age-days` (default 14) and no open pull request names it | it is abandoned work; the tag keeps it |

Archiving means: create the tag `archive/<branch>` at the tip (with `@<sha7>` appended when a
tag of that name already points elsewhere), then delete the branch. `main` and `flux/*` are
never touched, because Flux image automation writes `flux/*` as its mailbox. A branch with an
open pull request is never touched.

## How it runs

`.github/workflows/branch-archive.yml` runs weekly (`41 3 * * 1`) on the workflow's own
`GITHUB_TOKEN` with `contents: write`; no credential is minted or stored (R52). The drill
catalogue row `branch-archive` in `drills/catalogue.yaml` grades that it ran inside 170 hours,
and `platform/drills/drill-dispatcher.yaml` dispatches it when GitHub's cron is late. Until it
is a Dagster schedule it is listed in `platform/scheduling/one-scheduler.yaml`, the ledger
`bin/idp-one-scheduler` keeps shrinking.

## Try it by hand

```
python3 bin/idp-branch-archive            # plan only, prints a summary
python3 bin/idp-branch-archive --apply    # push tags, delete branches
```

Output is a summary, never a log (LAW 55). Restore a branch with
`git push origin refs/tags/archive/<branch>:refs/heads/<branch>`.

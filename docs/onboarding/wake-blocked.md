# wake-blocked: onboarding

**What it is.** `bin/idp-wake-blocked`, run every 30 minutes per repo by `.github/workflows/wake-blocked.yml` (the caller in `platform/github/workflows/`, the logic in the composite action `.github/actions/wake-blocked`). A closed, unmerged PR whose body has `Blocked-by: <key>` lines is reopened, branch updated, the moment every key has landed. Ticket: crew#504 CP7.

**What you need to know.**
- Keys: `repo#N` or `owner/repo#N` (a PR counts as landed when merged, an issue when closed); anything else is free text and lands only through `workflow_dispatch` with `resolved=<key>`, or `--resolved` on the CLI. Several keys: comma-separated or one line each. All must land.
- Closing a PR as blocked: put the line in the body before closing. The line is the whole contract; no label, no graph.
- Cap: nothing wakes while the repo has 10 or more open PRs (`PR_CAP`); the run prints `capped` for it and tries again next tick.
- The branch update is GitHub's `update-branch` (a merge of base into the branch). No local checkout, no force push. A conflict reopens with `needs-rebase`.
- Permissions: the repo's own `GITHUB_TOKEN` (`pull-requests: write`, `issues: write`); blockers in other estate repos are read anonymously, which works because every estate repo is public.

**How to turn it off.** Delete `.github/workflows/wake-blocked.yml` in the repo, or remove the `Blocked-by:` line from a PR you want to stay closed.

**How to know it is working.** The workflow's step summary ends with `wake-blocked: N sleeping, M woke, K capped`; `tests/test_incident_crew504_blocked_pr_wakes_when_blocker_lands.py` proves wake, sleep, silence, cap and free-text both ways.

# Onboarding: actions-pinned

## What it is

`bin/actions-pinned [DIR]` reads every `uses:` line under `.github/workflows`
and checks that the reference ends in a 40-character hex commit SHA. `./local`
paths and `docker://` references are exempt, since those cannot be repointed by
a third party the way a tag on a marketplace action can.

## Why it exists

An action pinned to a tag (`@v4`) or a branch can be repointed by whoever owns
that action, after your workflow has already been reviewed and merged. The
tj-actions incident in March 2025 is the reference case: a popular action's tag
was moved to point at code that dumped CI secrets, and every workflow still
trusting the tag ran it. A commit SHA cannot be moved, so pinning to one closes
that door regardless of who controls the action's repository.

## When it runs

It is a standalone check, run by hand or from a script — it is not currently
wired into `bin/idp-ci` or a workflow step. `.github/dependabot.yml` is
configured to open weekly PRs that bump the pinned SHAs when an action
publishes a new release, so pins do not go stale even though nothing pins
enforces them at merge time.

## Related files

```
bin/actions-pinned                        the check
.github/dependabot.yml                    keeps the pinned SHAs current
docs/reference/security-policy.md         control A.5.21 cites this command
docs/demo/security-policy.md              a working run in that control's context
docs/onboarding/security-policy.md        the wider security-policy control set
```

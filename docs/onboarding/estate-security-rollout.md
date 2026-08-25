# Onboarding: estate-security-rollout

## What it is

`bin/estate-security-rollout [--apply] [--merge]` makes sure every repository
pushed in the last `ACTIVE_DAYS` (30) days carries
`.github/workflows/security-scan.yml`, byte-identical to
`platform/github/workflows/security-scan.yml` in idp. That file is two jobs,
`security-scan` and `spec-gate`, each one `uses:` line calling a composite
action in idp. Report mode prints `ok`, `MISSING`, `OPEN` or `BLOCKED` per
repository. `--apply` writes the file on branch `estate/security-scan` through
the GitHub contents API and opens one pull request per repository. `--merge`
squash-merges the pull requests whose checks are green. Idempotent: a second
run reports `ok` for what is in place and touches nothing.

## Why it exists

Founder, 2026-08-25: the security scan and the executable-spec rule apply to
the whole estate, "only active ones", and the ways of working are unified in
one shot. 50 repositories, 28 active; 15 of the active ones had no CI at all.
A required status check is matched by job name, so the job has to exist in a
repository before `repo-rulesets` can require it there. This command is the
first half; `bin/repo-rulesets --apply` with
`platform/github/ruleset.@active.security-scan.json` is the second.

## The deviation from actions-pinned

The caller uses `chidionyema/idp/.github/actions/...@main`, a moving ref on a
same-owner repository, where `bin/actions-pinned` demands a commit SHA for
third-party actions. A SHA would have to be re-pinned in 27 repositories on
every idp change. The risk a SHA guards against is the action's owner moving a
tag after review; the owner here is the estate.

## What it cannot see

Repositories that answer 403 (private on the free plan) print `BLOCKED`. A
repository with a `review-gate` of its own (crew) needs its reviewer comment
before `--merge` can land it; the command reports it `OPEN`.

## Related files

```
bin/estate-security-rollout                       this command
platform/github/workflows/security-scan.yml       the caller every repo carries
.github/actions/security-scan/action.yml          gate 1
.github/actions/spec-gate/action.yml              gate 2
platform/github/ruleset.@active.security-scan.json
                                                  makes both checks required on active repos
bin/repo-rulesets                                 applies the rulesets
```

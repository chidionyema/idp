# Onboarding: repo-rulesets

## What it is

`bin/repo-rulesets` puts one GitHub ruleset —
`platform/github/ruleset.default-branch.json`, which refuses deletion and
force-push on the default branch — on every repository under the estate
GitHub account. It is a loop over `gh api`, per repository, report mode by
default; `--apply` creates the ruleset where it is missing and updates it
(PUT) where it has drifted from the spec file. An existing ruleset of the same
name is treated as the same one and updated, never duplicated.

## Why it exists

GitHub's org-wide `~ALL` ruleset target only exists for organizations, and the
estate's GitHub account is a User (`gh api /users/<owner> -q .type`
confirms this). So there is no single account-level setting to protect every
repository's default branch at once — this script is the substitute, applying
the one ruleset spec to each repository individually and reporting which ones
already match, which have drifted, and which do not have it at all.

## When it runs

By hand, in report mode, whenever a new repository has been created and needs
checking. `docs/reference/security-policy.md` cites it as the proof for
control A.8.4 (default branch deletion/force-push protection).

## What it cannot see

A private repository on GitHub's free plan answers 403 to the rulesets API.
Those repositories print `BLOCKED`, never silently skipped, because a 403 is
not the same fact as "protected" or "not protected" — it means the check could
not run at all.

## Related files

```
bin/repo-rulesets                              the loop, report or --apply
platform/github/ruleset.default-branch.json    the one ruleset spec
docs/onboarding/ports.md                       cites this under its own heading
docs/reference/security-policy.md              control A.8.4 cites this command
```

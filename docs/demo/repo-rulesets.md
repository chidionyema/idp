# Demo: repo-rulesets

`bin/repo-rulesets [--apply]` puts
`platform/github/ruleset.default-branch.json` (no deletion, no force-push on
the default branch) on every repository under the estate GitHub account.
Report mode by default; `--apply` creates or updates. Run against the real
account:

```
$ bin/repo-rulesets
ok      crew: estate-default-branch-protection #21333326
ok      estate: estate-default-branch-protection #21336575
BLOCKED estate-secrets: private on the free plan (403); make it public or upgrade
ok      idp: estate-default-branch-protection #21333351
BLOCKED hermes-agent: private on the free plan (403); make it public or upgrade
...
MISSING tailwind-css-starter-blog: no ruleset estate-default-branch-protection
...
FAIL  rulesets 47 carry estate-default-branch-protection, 1 missing or drifted, 2 private repos blocked by plan
```

That is the account's real, current state: 47 of the account's public
repositories carry the ruleset, one (`tailwind-css-starter-blog`) does not
yet, and two private repositories on the free plan cannot be checked at all —
the rulesets API answers 403 for a private repo on that plan, and the script
prints `BLOCKED` for that case rather than silently skipping it. A repository
whose ruleset exists but differs from `platform/github/ruleset.default-
branch.json` prints `DRIFT` instead of `MISSING`. Every non-ok row makes the
final line `FAIL` and the command exit non-zero; a clean account prints `ok`
and exits 0. `--apply` turns each `MISSING`/`DRIFT` into `FIXED` by creating
or updating (PUT) the ruleset, which is idempotent — running it twice makes no
further change the second time.

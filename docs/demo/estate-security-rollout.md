# Demo: estate-security-rollout

One command installs the two estate gates in every active repository.
Report mode first (founder machine, 2026-08-25, before the rollout):

```
$ bin/estate-security-rollout | tail -4
MISSING sentinel-loop: no .github/workflows/security-scan.yml on main
MISSING survival-stack: no .github/workflows/security-scan.yml on main
MISSING tailwind-css-starter-blog: no .github/workflows/security-scan.yml on main
FAIL  rollout 1 in place, 0 opened, 0 merged, 27 open or missing, 0 blocked
```

Then open the pull requests, and merge the green ones:

```
$ bin/estate-security-rollout --apply | tail -2
OPENED  survival-stack: https://github.com/chidionyema/survival-stack/pull/N
FAIL  rollout 1 in place, 27 opened, 0 merged, 0 open or missing, 0 blocked
$ bin/estate-security-rollout --merge | tail -1
ok    rollout 28 in place, 0 opened, 27 merged, 0 open or missing, 0 blocked
$ bin/repo-rulesets --apply | grep estate-security-scan | head -2
FIXED   crew: created #NNN
```

A repository whose history holds a leaked secret stays `OPEN`: its
`security-scan` check is red and the pull request is not merged. That is the
gate working; clean the history, then run `--merge` again.

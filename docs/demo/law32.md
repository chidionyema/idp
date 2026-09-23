# LAW 32 gate — what it looks like when it runs

Real output, captured on the branch that added it, 2026-08-25.

## A new bin file that has its pair

```
$ bin/law32-gate --added bin/supply-chain
ok    law32 1 new bin file(s) carry a demo+onboarding pair; 18 page(s) above the 200-char floor and in the nav
```

## A new bin file that has none

```
$ bin/law32-gate --added bin/feature-with-no-pages; echo rc=$?
FAIL  law32 bin/feature-with-no-pages: no docs/demo/<n>.md + docs/onboarding/<n>.md for a feature named <n> where <n> is 'feature-with-no-pages' or a hyphen-prefix of it
rc=1
```

## The same gate pointed at main before this branch

Every demo and onboarding page existed and none was in the portal's nav, so the
founder could not see any of them. The gate says so, once per page:

```
FAIL  law32 docs/demo/idp.md: not in mkdocs.yml nav, so the portal never shows it
FAIL  law32 docs/demo/mcp.md: not in mkdocs.yml nav, so the portal never shows it
FAIL  law32 docs/demo/placement.md: not in mkdocs.yml nav, so the portal never shows it
```

## In the pull request

`bin/idp-ci` runs the good case, the bad case and the real diff in one row, so a
pull request that adds a bin file without its two pages goes red in `offline-gate`.

# Delivery: right first time

Generated 2026-09-03T07:16:10Z, window since 2026-08-20 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 98; with checks on the first commit: 83; no checks recorded: 15.
**Green on the first push** (one commit, every check passed): 18/83 = 22%.
Commits per merged pull request: median 2, most 24; needing a second commit: 59/98.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 890 | 890 | 100% | 0 |
| build-multiarch | 17 | 17 | 100% | 0 |
| ci | 13 | 17 | 76% | 0 |
| estate-state | 15 | 15 | 100% | 0 |
| login-drill | 7 | 7 | 100% | 0 |
| ticket-verification | 6 | 6 | 100% | 0 |
| verdict-signoz | 0 | 6 | 0% | 0 |
| verdict-backstage | 6 | 6 | 100% | 0 |
| storefront-drill | 5 | 5 | 100% | 0 |
| otto-parity | 0 | 5 | 0% | 0 |
| verdict-langfuse | 4 | 5 | 80% | 0 |
| stale | 5 | 5 | 100% | 0 |
| oke-check | 0 | 3 | 0% | 0 |

**All runs on main: 968/987 = 98% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 56; with checks on the first commit: 50; no checks recorded: 6.
**Green on the first push** (one commit, every check passed): 31/50 = 62%.
Commits per merged pull request: median 1, most 13; needing a second commit: 25/56.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 150 | 329 | 46% | 0 |
| Merge when green | 268 | 277 | 97% | 0 |
| Approve parked runs | 113 | 115 | 98% | 0 |
| Live storefront smoke | 58 | 75 | 77% | 0 |
| CI | 58 | 66 | 88% | 0 |
| container images | 61 | 62 | 98% | 0 |
| k8s manifests | 44 | 44 | 100% | 0 |
| DNS drift drill | 9 | 11 | 82% | 0 |
| stale | 7 | 7 | 100% | 0 |
| Deploy Store.Api | 0 | 3 | 0% | 0 |

**All runs on main: 768/989 = 78% passed on the first attempt; 0 re-runs.**

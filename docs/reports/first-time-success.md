# Delivery: right first time

Generated 2026-09-20T07:49:53Z, window since 2026-09-06 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 85; with checks on the first commit: 82; no checks recorded: 3.
**Green on the first push** (one commit, every check passed): 4/82 = 5%.
Commits per merged pull request: median 3, most 100; needing a second commit: 80/85.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 165 | 858 | 19% | 0 |
| estate-state | 33 | 33 | 100% | 0 |
| ticket-verification | 12 | 12 | 100% | 0 |
| storefront-drill | 0 | 10 | 0% | 0 |
| otto-parity | 0 | 10 | 0% | 0 |
| verdict-backstage | 9 | 9 | 100% | 0 |
| verdict-langfuse | 0 | 9 | 0% | 0 |
| stale | 9 | 9 | 100% | 0 |
| login-drill | 0 | 9 | 0% | 0 |
| verdict-signoz | 0 | 9 | 0% | 0 |
| name-drift | 0 | 3 | 0% | 0 |
| estate-escrow | 3 | 3 | 100% | 0 |

**All runs on main: 231/974 = 24% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 4; with checks on the first commit: 3; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 3/3 = 100%.
Commits per merged pull request: median 1, most 26; needing a second commit: 1/4.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 103 | 125 | 82% | 0 |
| Approve parked runs | 97 | 97 | 100% | 0 |
| Live storefront smoke | 0 | 34 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |
| container images | 4 | 4 | 100% | 0 |
| CI | 3 | 4 | 75% | 0 |

**All runs on main: 221/292 = 76% passed on the first attempt; 0 re-runs.**

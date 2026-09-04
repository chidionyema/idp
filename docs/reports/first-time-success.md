# Delivery: right first time

Generated 2026-09-04T07:19:30Z, window since 2026-08-21 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 98; with checks on the first commit: 92; no checks recorded: 6.
**Green on the first push** (one commit, every check passed): 8/92 = 9%.
Commits per merged pull request: median 1, most 72; needing a second commit: 32/98.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 908 | 908 | 100% | 0 |
| build-multiarch | 17 | 17 | 100% | 0 |
| ci | 9 | 17 | 53% | 0 |
| estate-state | 12 | 13 | 92% | 0 |
| ticket-verification | 4 | 4 | 100% | 0 |
| storefront-drill | 4 | 4 | 100% | 0 |
| verdict-signoz | 0 | 4 | 0% | 0 |
| verdict-backstage | 4 | 4 | 100% | 0 |
| stale | 4 | 4 | 100% | 0 |
| otto-parity | 0 | 3 | 0% | 0 |
| verdict-langfuse | 3 | 3 | 100% | 0 |
| login-drill | 3 | 3 | 100% | 0 |

**All runs on main: 968/984 = 98% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 56; with checks on the first commit: 50; no checks recorded: 6.
**Green on the first push** (one commit, every check passed): 30/50 = 60%.
Commits per merged pull request: median 1, most 13; needing a second commit: 26/56.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 155 | 332 | 47% | 0 |
| Merge when green | 257 | 266 | 97% | 0 |
| Approve parked runs | 117 | 119 | 98% | 0 |
| Live storefront smoke | 57 | 80 | 71% | 0 |
| CI | 57 | 66 | 86% | 0 |
| container images | 63 | 64 | 98% | 0 |
| k8s manifests | 44 | 44 | 100% | 0 |
| DNS drift drill | 9 | 11 | 82% | 0 |
| stale | 8 | 8 | 100% | 0 |

**All runs on main: 767/990 = 77% passed on the first attempt; 0 re-runs.**

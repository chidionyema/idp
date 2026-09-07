# Delivery: right first time

Generated 2026-09-07T02:37:10Z, window since 2026-08-24 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 99; with checks on the first commit: 96; no checks recorded: 3.
**Green on the first push** (one commit, every check passed): 27/96 = 28%.
Commits per merged pull request: median 1, most 4; needing a second commit: 15/99.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 920 | 920 | 100% | 0 |
| build-multiarch | 16 | 16 | 100% | 0 |
| ci | 12 | 15 | 80% | 0 |
| estate-state | 1 | 10 | 10% | 0 |
| ticket-verification | 3 | 3 | 100% | 0 |
| otto-parity | 0 | 3 | 0% | 0 |
| verdict-signoz | 0 | 3 | 0% | 0 |
| verdict-backstage | 3 | 3 | 100% | 0 |

**All runs on main: 955/973 = 98% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 60; with checks on the first commit: 54; no checks recorded: 6.
**Green on the first push** (one commit, every check passed): 31/54 = 57%.
Commits per merged pull request: median 1, most 26; needing a second commit: 29/60.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 162 | 342 | 47% | 0 |
| Merge when green | 215 | 224 | 96% | 0 |
| Approve parked runs | 119 | 121 | 98% | 0 |
| Live storefront smoke | 57 | 108 | 53% | 0 |
| container images | 64 | 65 | 98% | 0 |
| CI | 54 | 65 | 83% | 0 |
| k8s manifests | 40 | 40 | 100% | 0 |
| DNS drift drill | 10 | 14 | 71% | 0 |
| stale | 11 | 11 | 100% | 0 |

**All runs on main: 732/990 = 74% passed on the first attempt; 0 re-runs.**

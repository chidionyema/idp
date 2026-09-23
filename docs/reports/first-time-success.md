# Delivery: right first time

Generated 2026-09-07T07:25:57Z, window since 2026-08-24 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 99; with checks on the first commit: 99; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 20/99 = 20%.
Commits per merged pull request: median 1, most 4; needing a second commit: 10/99.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 933 | 933 | 100% | 0 |
| build-multiarch | 14 | 14 | 100% | 0 |
| ci | 11 | 12 | 92% | 0 |
| estate-state | 1 | 9 | 11% | 0 |
| ticket-verification | 3 | 3 | 100% | 0 |
| otto-parity | 0 | 3 | 0% | 0 |
| verdict-signoz | 0 | 3 | 0% | 0 |
| verdict-backstage | 3 | 3 | 100% | 0 |

**All runs on main: 965/980 = 98% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 60; with checks on the first commit: 54; no checks recorded: 6.
**Green on the first push** (one commit, every check passed): 31/54 = 57%.
Commits per merged pull request: median 1, most 26; needing a second commit: 29/60.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 161 | 341 | 47% | 0 |
| Merge when green | 214 | 223 | 96% | 0 |
| Approve parked runs | 120 | 122 | 98% | 0 |
| Live storefront smoke | 57 | 108 | 53% | 0 |
| container images | 64 | 65 | 98% | 0 |
| CI | 54 | 65 | 83% | 0 |
| k8s manifests | 40 | 40 | 100% | 0 |
| DNS drift drill | 10 | 14 | 71% | 0 |
| stale | 11 | 11 | 100% | 0 |

**All runs on main: 731/989 = 74% passed on the first attempt; 0 re-runs.**

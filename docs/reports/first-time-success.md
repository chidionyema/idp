# Delivery: right first time

Generated 2026-09-06T07:13:43Z, window since 2026-08-23 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 100; with checks on the first commit: 98; no checks recorded: 2.
**Green on the first push** (one commit, every check passed): 27/98 = 28%.
Commits per merged pull request: median 1, most 5; needing a second commit: 45/100.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 937 | 937 | 100% | 0 |
| build-multiarch | 14 | 14 | 100% | 0 |
| ci | 6 | 12 | 50% | 0 |
| estate-state | 1 | 6 | 17% | 0 |
| verdict-backstage | 4 | 4 | 100% | 0 |
| ticket-verification | 3 | 3 | 100% | 0 |
| otto-parity | 0 | 3 | 0% | 0 |
| verdict-signoz | 0 | 3 | 0% | 0 |
| login-drill | 2 | 3 | 67% | 0 |

**All runs on main: 967/985 = 98% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 57; with checks on the first commit: 52; no checks recorded: 5.
**Green on the first push** (one commit, every check passed): 29/52 = 56%.
Commits per merged pull request: median 1, most 13; needing a second commit: 28/57.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 165 | 338 | 49% | 0 |
| Merge when green | 229 | 238 | 96% | 0 |
| Approve parked runs | 124 | 126 | 98% | 0 |
| Live storefront smoke | 57 | 95 | 60% | 0 |
| container images | 63 | 64 | 98% | 0 |
| CI | 53 | 64 | 83% | 0 |
| k8s manifests | 42 | 42 | 100% | 0 |
| DNS drift drill | 10 | 13 | 77% | 0 |
| stale | 10 | 10 | 100% | 0 |

**All runs on main: 753/990 = 76% passed on the first attempt; 0 re-runs.**

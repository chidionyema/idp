# Delivery: right first time

Generated 2026-09-10T07:25:12Z, window since 2026-08-27 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 99; with checks on the first commit: 99; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 23/99 = 23%.
Commits per merged pull request: median 2, most 5; needing a second commit: 76/99.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| merge-when-green | 290 | 420 | 69% | 0 |
| deploy-when-green | 184 | 251 | 73% | 0 |
| flux-events | 160 | 160 | 100% | 0 |
| build-multiarch | 30 | 30 | 100% | 0 |
| ci | 28 | 29 | 97% | 0 |
| estate-state | 25 | 25 | 100% | 0 |
| ticket-verification | 9 | 9 | 100% | 0 |
| storefront-drill | 0 | 8 | 0% | 0 |
| otto-parity | 0 | 8 | 0% | 0 |
| verdict-signoz | 0 | 8 | 0% | 0 |
| verdict-backstage | 0 | 8 | 0% | 0 |
| verdict-langfuse | 0 | 8 | 0% | 0 |
| stale | 8 | 8 | 100% | 0 |
| login-drill | 0 | 8 | 0% | 0 |
| name-drift | 0 | 3 | 0% | 0 |

**All runs on main: 734/983 = 75% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 41; with checks on the first commit: 37; no checks recorded: 4.
**Green on the first push** (one commit, every check passed): 22/37 = 59%.
Commits per merged pull request: median 1, most 26; needing a second commit: 19/41.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 113 | 223 | 51% | 0 |
| Live storefront smoke | 49 | 102 | 48% | 0 |
| Approve parked runs | 87 | 87 | 100% | 0 |
| Merge when green | 87 | 87 | 100% | 0 |
| container images | 41 | 41 | 100% | 0 |
| CI | 33 | 41 | 80% | 0 |
| k8s manifests | 20 | 20 | 100% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 9 | 14 | 64% | 0 |

**All runs on main: 453/629 = 72% passed on the first attempt; 0 re-runs.**

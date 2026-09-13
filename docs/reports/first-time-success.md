# Delivery: right first time

Generated 2026-09-13T07:35:02Z, window since 2026-08-30 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 97; with checks on the first commit: 90; no checks recorded: 7.
**Green on the first push** (one commit, every check passed): 10/90 = 11%.
Commits per merged pull request: median 2, most 58; needing a second commit: 80/97.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| merge-when-green | 229 | 312 | 73% | 0 |
| deploy-when-green | 219 | 312 | 70% | 0 |
| flux-events | 199 | 199 | 100% | 0 |
| build-multiarch | 33 | 34 | 97% | 0 |
| ci | 34 | 34 | 100% | 0 |
| estate-state | 22 | 22 | 100% | 0 |
| ticket-verification | 9 | 9 | 100% | 0 |
| login-drill | 0 | 9 | 0% | 0 |
| verdict-backstage | 0 | 8 | 0% | 0 |
| verdict-langfuse | 0 | 8 | 0% | 0 |
| storefront-drill | 7 | 7 | 100% | 0 |
| otto-parity | 0 | 7 | 0% | 0 |
| verdict-signoz | 0 | 7 | 0% | 0 |
| stale | 7 | 7 | 100% | 0 |
| conscience-ask | 0 | 3 | 0% | 0 |

**All runs on main: 759/978 = 78% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 30; with checks on the first commit: 26; no checks recorded: 4.
**Green on the first push** (one commit, every check passed): 17/26 = 65%.
Commits per merged pull request: median 1, most 26; needing a second commit: 13/30.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 121 | 207 | 58% | 0 |
| Live storefront smoke | 41 | 102 | 40% | 0 |
| Approve parked runs | 98 | 98 | 100% | 0 |
| Merge when green | 43 | 43 | 100% | 0 |
| container images | 30 | 30 | 100% | 0 |
| CI | 23 | 30 | 77% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 6 | 14 | 43% | 0 |
| k8s manifests | 11 | 11 | 100% | 0 |

**All runs on main: 387/549 = 70% passed on the first attempt; 0 re-runs.**

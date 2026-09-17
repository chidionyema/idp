# Delivery: right first time

Generated 2026-09-17T07:49:07Z, window since 2026-09-03 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 94; with checks on the first commit: 89; no checks recorded: 5.
**Green on the first push** (one commit, every check passed): 2/89 = 2%.
Commits per merged pull request: median 3, most 77; needing a second commit: 92/94.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 410 | 430 | 95% | 0 |
| merge-when-green | 135 | 176 | 77% | 0 |
| deploy-when-green | 122 | 176 | 69% | 0 |
| estate-state | 36 | 36 | 100% | 0 |
| scorecard | 0 | 16 | 0% | 0 |
| build-multiarch | 1 | 16 | 6% | 0 |
| .github/workflows/estate-dag-gen.yml | 0 | 16 | 0% | 0 |
| ci | 15 | 15 | 100% | 0 |
| ticket-verification | 12 | 12 | 100% | 0 |
| storefront-drill | 10 | 10 | 100% | 0 |
| stale | 10 | 10 | 100% | 0 |
| login-drill | 0 | 10 | 0% | 0 |
| otto-parity | 0 | 10 | 0% | 0 |
| verdict-signoz | 0 | 10 | 0% | 0 |
| verdict-backstage | 0 | 10 | 0% | 0 |
| verdict-langfuse | 0 | 10 | 0% | 0 |
| ping | 0 | 3 | 0% | 0 |
| name-drift | 0 | 3 | 0% | 0 |
| conscience-ask | 0 | 3 | 0% | 0 |
| estate-escrow | 3 | 3 | 100% | 0 |

**All runs on main: 754/975 = 77% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 11; with checks on the first commit: 10; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 6/10 = 60%.
Commits per merged pull request: median 1, most 26; needing a second commit: 5/11.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 110 | 150 | 73% | 0 |
| Approve parked runs | 99 | 99 | 100% | 0 |
| Live storefront smoke | 0 | 55 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 2 | 14 | 14% | 0 |
| container images | 11 | 11 | 100% | 0 |
| CI | 8 | 11 | 73% | 0 |
| k8s manifests | 3 | 3 | 100% | 0 |

**All runs on main: 247/357 = 69% passed on the first attempt; 0 re-runs.**

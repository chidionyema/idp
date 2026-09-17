# Delivery: right first time

Generated 2026-09-17T22:43:53Z, window since 2026-09-03 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 72; with checks on the first commit: 71; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 1/71 = 1%.
Commits per merged pull request: median 3, most 100; needing a second commit: 71/72.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 500 | 511 | 98% | 0 |
| deploy-when-green | 105 | 133 | 79% | 0 |
| merge-when-green | 108 | 131 | 82% | 0 |
| estate-state | 37 | 37 | 100% | 0 |
| conscience-ask | 0 | 17 | 0% | 0 |
| verdict-backstage | 9 | 15 | 60% | 0 |
| login-drill | 0 | 14 | 0% | 0 |
| ticket-verification | 14 | 14 | 100% | 0 |
| verdict-signoz | 0 | 12 | 0% | 0 |
| storefront-drill | 7 | 11 | 64% | 0 |
| otto-parity | 0 | 11 | 0% | 0 |
| verdict-langfuse | 0 | 11 | 0% | 0 |
| stale | 10 | 10 | 100% | 0 |
| .github/workflows/estate-dag-gen.yml | 0 | 8 | 0% | 0 |
| build-multiarch | 3 | 7 | 43% | 0 |
| scorecard | 0 | 7 | 0% | 0 |
| ci | 4 | 7 | 57% | 0 |
| demo-sandbox | 3 | 3 | 100% | 0 |
| agents-md-gate | 3 | 3 | 100% | 0 |
| webhook-diagnose-v2 | 1 | 3 | 33% | 0 |
| name-drift | 0 | 3 | 0% | 0 |
| estate-escrow | 3 | 3 | 100% | 0 |

**All runs on main: 807/971 = 83% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 11; with checks on the first commit: 10; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 6/10 = 60%.
Commits per merged pull request: median 1, most 26; needing a second commit: 5/11.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 114 | 157 | 73% | 0 |
| Approve parked runs | 103 | 103 | 100% | 0 |
| Live storefront smoke | 0 | 56 | 0% | 0 |
| stale | 15 | 15 | 100% | 0 |
| DNS drift drill | 2 | 15 | 13% | 0 |
| container images | 11 | 11 | 100% | 0 |
| CI | 8 | 11 | 73% | 0 |
| k8s manifests | 3 | 3 | 100% | 0 |

**All runs on main: 256/371 = 69% passed on the first attempt; 0 re-runs.**

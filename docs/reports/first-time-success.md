# Delivery: right first time

Generated 2026-09-19T07:27:11Z, window since 2026-09-05 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 73; with checks on the first commit: 71; no checks recorded: 2.
**Green on the first push** (one commit, every check passed): 4/71 = 6%.
Commits per merged pull request: median 3, most 100; needing a second commit: 68/73.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 601 | 616 | 98% | 0 |
| merge-when-green | 65 | 77 | 84% | 0 |
| deploy-when-green | 60 | 77 | 78% | 0 |
| estate-state | 45 | 45 | 100% | 0 |
| ticket-verification | 17 | 17 | 100% | 0 |
| storefront-drill | 0 | 14 | 0% | 0 |
| otto-parity | 0 | 14 | 0% | 0 |
| verdict-signoz | 0 | 14 | 0% | 0 |
| verdict-langfuse | 0 | 14 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| login-drill | 0 | 14 | 0% | 0 |
| verdict-backstage | 13 | 13 | 100% | 0 |
| ci | 7 | 7 | 100% | 0 |
| scorecard | 0 | 7 | 0% | 0 |
| build-multiarch | 1 | 7 | 14% | 0 |
| .github/workflows/estate-dag-gen.yml | 0 | 7 | 0% | 0 |
| conscience-ask | 0 | 5 | 0% | 0 |
| name-drift | 0 | 4 | 0% | 0 |
| estate-escrow | 4 | 4 | 100% | 0 |
| ping | 0 | 4 | 0% | 0 |
| catalog-render | 3 | 3 | 100% | 0 |
| pr-age | 0 | 3 | 0% | 0 |
| vault-reads | 0 | 3 | 0% | 0 |
| conscience | 3 | 3 | 100% | 0 |
| pr-consolidate | 3 | 3 | 100% | 0 |
| wake-blocked | 3 | 3 | 100% | 0 |
| demo-sandbox | 3 | 3 | 100% | 0 |

**All runs on main: 842/995 = 85% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 7; with checks on the first commit: 6; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 5/6 = 83%.
Commits per merged pull request: median 1, most 26; needing a second commit: 2/7.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 107 | 134 | 80% | 0 |
| Approve parked runs | 98 | 98 | 100% | 0 |
| Live storefront smoke | 0 | 39 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |
| container images | 7 | 7 | 100% | 0 |
| CI | 6 | 7 | 86% | 0 |

**All runs on main: 232/313 = 74% passed on the first attempt; 0 re-runs.**

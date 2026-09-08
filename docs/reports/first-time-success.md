# Delivery: right first time

Generated 2026-09-08T02:37:08Z, window since 2026-08-25 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 99; with checks on the first commit: 92; no checks recorded: 7.
**Green on the first push** (one commit, every check passed): 37/92 = 40%.
Commits per merged pull request: median 2, most 9; needing a second commit: 51/99.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 641 | 641 | 100% | 0 |
| build-multiarch | 90 | 92 | 98% | 0 |
| ci | 82 | 92 | 89% | 0 |
| estate-state | 36 | 36 | 100% | 0 |
| login-drill | 7 | 22 | 32% | 0 |
| verdict-backstage | 1 | 14 | 7% | 0 |
| ticket-verification | 13 | 13 | 100% | 0 |
| verdict-signoz | 0 | 11 | 0% | 0 |
| verdict-langfuse | 0 | 11 | 0% | 0 |
| storefront-drill | 10 | 10 | 100% | 0 |
| otto-parity | 0 | 10 | 0% | 0 |
| stale | 10 | 10 | 100% | 0 |
| .github/workflows/founder-word.yml | 0 | 7 | 0% | 0 |
| conscience-ask | 0 | 7 | 0% | 0 |
| catalog-render | 3 | 3 | 100% | 0 |
| name-drift | 0 | 3 | 0% | 0 |
| demo-sandbox | 3 | 3 | 100% | 0 |
| estate-escrow | 3 | 3 | 100% | 0 |
| ping | 0 | 3 | 0% | 0 |

**All runs on main: 899/991 = 91% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 60; with checks on the first commit: 54; no checks recorded: 6.
**Green on the first push** (one commit, every check passed): 31/54 = 57%.
Commits per merged pull request: median 1, most 26; needing a second commit: 29/60.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 165 | 344 | 48% | 0 |
| Merge when green | 210 | 219 | 96% | 0 |
| Approve parked runs | 123 | 125 | 98% | 0 |
| Live storefront smoke | 57 | 110 | 52% | 0 |
| container images | 63 | 64 | 98% | 0 |
| CI | 52 | 63 | 83% | 0 |
| k8s manifests | 39 | 39 | 100% | 0 |
| DNS drift drill | 10 | 15 | 67% | 0 |
| stale | 12 | 12 | 100% | 0 |

**All runs on main: 731/991 = 74% passed on the first attempt; 0 re-runs.**

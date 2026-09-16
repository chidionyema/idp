# Delivery: right first time

Generated 2026-09-16T07:48:23Z, window since 2026-09-02 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 93; with checks on the first commit: 83; no checks recorded: 10.
**Green on the first push** (one commit, every check passed): 18/83 = 22%.
Commits per merged pull request: median 3, most 20; needing a second commit: 74/93.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 391 | 392 | 100% | 0 |
| merge-when-green | 131 | 168 | 78% | 0 |
| deploy-when-green | 121 | 168 | 72% | 0 |
| estate-state | 51 | 51 | 100% | 0 |
| ticket-verification | 19 | 19 | 100% | 0 |
| scorecard | 0 | 17 | 0% | 0 |
| build-multiarch | 4 | 17 | 24% | 0 |
| ci | 16 | 16 | 100% | 0 |
| verdict-signoz | 0 | 16 | 0% | 0 |
| storefront-drill | 15 | 15 | 100% | 0 |
| otto-parity | 0 | 15 | 0% | 0 |
| verdict-backstage | 0 | 15 | 0% | 0 |
| verdict-langfuse | 0 | 15 | 0% | 0 |
| stale | 15 | 15 | 100% | 0 |
| login-drill | 0 | 15 | 0% | 0 |
| conscience-ask | 0 | 6 | 0% | 0 |
| catalog-render | 4 | 4 | 100% | 0 |
| name-drift | 0 | 4 | 0% | 0 |
| wake-blocked | 4 | 4 | 100% | 0 |
| estate-escrow | 4 | 4 | 100% | 0 |
| demo-sandbox | 4 | 4 | 100% | 0 |
| pr-age | 0 | 3 | 0% | 0 |
| vault-reads | 0 | 3 | 0% | 0 |
| conscience | 2 | 3 | 67% | 0 |
| ping | 0 | 3 | 0% | 0 |

**All runs on main: 781/992 = 79% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 14; with checks on the first commit: 12; no checks recorded: 2.
**Green on the first push** (one commit, every check passed): 7/12 = 58%.
Commits per merged pull request: median 2, most 26; needing a second commit: 7/14.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 112 | 162 | 69% | 0 |
| Approve parked runs | 100 | 100 | 100% | 0 |
| Live storefront smoke | 5 | 63 | 8% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 3 | 14 | 21% | 0 |
| container images | 14 | 14 | 100% | 0 |
| CI | 9 | 14 | 64% | 0 |
| k8s manifests | 5 | 5 | 100% | 0 |

**All runs on main: 262/386 = 68% passed on the first attempt; 0 re-runs.**

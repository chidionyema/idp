# Delivery: right first time

Generated 2026-09-15T07:53:22Z, window since 2026-09-01 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 98; with checks on the first commit: 90; no checks recorded: 8.
**Green on the first push** (one commit, every check passed): 16/90 = 18%.
Commits per merged pull request: median 3, most 71; needing a second commit: 81/98.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| flux-events | 284 | 303 | 94% | 0 |
| merge-when-green | 168 | 252 | 67% | 0 |
| deploy-when-green | 161 | 250 | 64% | 0 |
| estate-state | 33 | 33 | 100% | 0 |
| build-multiarch | 10 | 22 | 45% | 0 |
| ci | 20 | 22 | 91% | 0 |
| scorecard | 0 | 15 | 0% | 0 |
| ticket-verification | 11 | 11 | 100% | 0 |
| login-drill | 0 | 11 | 0% | 0 |
| storefront-drill | 9 | 9 | 100% | 0 |
| stale | 9 | 9 | 100% | 0 |
| verdict-signoz | 0 | 9 | 0% | 0 |
| verdict-backstage | 0 | 9 | 0% | 0 |
| otto-parity | 0 | 8 | 0% | 0 |
| verdict-langfuse | 0 | 8 | 0% | 0 |
| conscience-ask | 0 | 4 | 0% | 0 |
| name-drift | 0 | 3 | 0% | 0 |
| estate-escrow | 3 | 3 | 100% | 0 |

**All runs on main: 708/981 = 72% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 16; with checks on the first commit: 14; no checks recorded: 2.
**Green on the first push** (one commit, every check passed): 9/14 = 64%.
Commits per merged pull request: median 1, most 26; needing a second commit: 7/16.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 114 | 169 | 67% | 0 |
| Approve parked runs | 100 | 100 | 100% | 0 |
| Live storefront smoke | 10 | 69 | 14% | 0 |
| container images | 16 | 16 | 100% | 0 |
| CI | 11 | 16 | 69% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 4 | 14 | 29% | 0 |
| k8s manifests | 6 | 6 | 100% | 0 |

**All runs on main: 275/404 = 68% passed on the first attempt; 0 re-runs.**

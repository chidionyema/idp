# Delivery: right first time

Generated 2026-10-09T09:15:21Z, window since 2026-09-25 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 94; with checks on the first commit: 94; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 14/94 = 15%.
Commits per merged pull request: median 1, most 6; needing a second commit: 32/94.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| greenlane | 173 | 377 | 46% | 0 |
| flux-events | 181 | 181 | 100% | 0 |
| deploy-when-green | 115 | 140 | 82% | 0 |
| merge-when-green | 118 | 139 | 85% | 0 |
| factory-ci | 19 | 19 | 100% | 0 |
| build-multiarch | 16 | 19 | 84% | 0 |
| portal-app | 14 | 17 | 82% | 1 |
| scorecard | 9 | 17 | 53% | 0 |
| guarded-paths | 17 | 17 | 100% | 0 |
| no-harness-folders | 17 | 17 | 100% | 0 |
| ci | 0 | 17 | 0% | 0 |
| verdict-backstage | 6 | 6 | 100% | 0 |
| ruff-required | 4 | 4 | 100% | 0 |
| Build & Release Backstage | 0 | 3 | 0% | 0 |
| ticket-verification | 3 | 3 | 100% | 0 |

**All runs on main: 692/976 = 71% passed on the first attempt; 1 re-runs.**

## chidionyema/prospector

Merged pull requests: 0; with checks on the first commit: 0; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 0/0 = no graded pull requests.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 71 | 79 | 90% | 0 |
| Approve parked runs | 70 | 70 | 100% | 0 |
| Live storefront smoke | 0 | 19 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |

**All runs on main: 155/196 = 79% passed on the first attempt; 0 re-runs.**

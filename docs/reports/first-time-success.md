# Delivery: right first time

Generated 2026-11-21T09:56:15Z, window since 2026-11-07 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 77; with checks on the first commit: 77; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 59/77 = 77%.
Commits per merged pull request: median 1, most 2; needing a second commit: 2/77.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| greenlane-common-failure-reaction | 120 | 366 | 33% | 0 |
| greenlane | 124 | 357 | 35% | 0 |
| merge-when-green | 50 | 52 | 96% | 0 |
| deploy-when-green | 49 | 51 | 96% | 0 |
| lane-feedback | 20 | 50 | 40% | 0 |
| .github/workflows/incident-loop.yml | 0 | 10 | 0% | 0 |
| factory-ci | 8 | 9 | 89% | 0 |
| estate-issueops | 0 | 8 | 0% | 0 |
| build-multiarch | 4 | 8 | 50% | 0 |
| scorecard | 8 | 8 | 100% | 0 |
| deterministic-zero-agent-cicd | 8 | 8 | 100% | 0 |
| no-harness-folders | 8 | 8 | 100% | 0 |
| guarded-paths | 8 | 8 | 100% | 0 |
| ci | 8 | 8 | 100% | 0 |
| context-index | 6 | 7 | 86% | 0 |
| portal-app | 7 | 7 | 100% | 0 |
| Push on main | 7 | 7 | 100% | 0 |
| ruff-required | 4 | 4 | 100% | 0 |
| agent (auto): LEGION #8398 | 0 | 3 | 0% | 0 |

**All runs on main: 439/979 = 45% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 1; with checks on the first commit: 0; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 0/0 = no graded pull requests.
Commits per merged pull request: median 6, most 6; needing a second commit: 1/1.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 55 | 83 | 66% | 0 |
| Approve parked runs | 53 | 53 | 100% | 0 |
| Live storefront smoke | 0 | 38 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |

**All runs on main: 122/202 = 60% passed on the first attempt; 0 re-runs.**

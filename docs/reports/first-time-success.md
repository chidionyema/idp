# Delivery: right first time

Generated 2026-11-20T10:09:27Z, window since 2026-11-06 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 70; with checks on the first commit: 67; no checks recorded: 3.
**Green on the first push** (one commit, every check passed): 47/67 = 70%.
Commits per merged pull request: median 1, most 15; needing a second commit: 7/70.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| greenlane-common-failure-reaction | 52 | 346 | 15% | 0 |
| greenlane | 52 | 338 | 15% | 0 |
| merge-when-green | 56 | 69 | 81% | 0 |
| deploy-when-green | 55 | 69 | 80% | 0 |
| lane-feedback | 31 | 68 | 46% | 0 |
| factory-ci | 8 | 8 | 100% | 0 |
| guarded-paths | 7 | 7 | 100% | 0 |
| no-harness-folders | 7 | 7 | 100% | 0 |
| scorecard | 7 | 7 | 100% | 0 |
| deterministic-zero-agent-cicd | 7 | 7 | 100% | 0 |
| portal-app | 7 | 7 | 100% | 0 |
| build-multiarch | 2 | 7 | 29% | 0 |
| context-index | 7 | 7 | 100% | 0 |
| .github/workflows/incident-loop.yml | 0 | 7 | 0% | 0 |
| Push on main | 7 | 7 | 100% | 0 |
| ci | 6 | 6 | 100% | 0 |
| ruff-required | 3 | 3 | 100% | 0 |

**All runs on main: 314/970 = 32% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 1; with checks on the first commit: 0; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 0/0 = no graded pull requests.
Commits per merged pull request: median 6, most 6; needing a second commit: 1/1.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 56 | 84 | 67% | 0 |
| Approve parked runs | 54 | 54 | 100% | 0 |
| Live storefront smoke | 0 | 38 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |

**All runs on main: 124/204 = 61% passed on the first attempt; 0 re-runs.**

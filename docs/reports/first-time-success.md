# Delivery: right first time

Generated 2026-11-28T10:34:57Z, window since 2026-11-14 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 72; with checks on the first commit: 72; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 46/72 = 64%.
Commits per merged pull request: median 1, most 3; needing a second commit: 16/72.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| greenlane-common-failure-reaction | 49 | 309 | 16% | 0 |
| greenlane | 48 | 290 | 17% | 0 |
| deploy-when-green | 67 | 67 | 100% | 0 |
| lane-feedback | 24 | 67 | 36% | 0 |
| merge-when-green | 66 | 66 | 100% | 0 |
| estate-issueops | 0 | 15 | 0% | 0 |
| scorecard | 13 | 14 | 93% | 0 |
| no-harness-folders | 13 | 13 | 100% | 0 |
| factory-ci | 10 | 13 | 77% | 0 |
| guarded-paths | 13 | 13 | 100% | 0 |
| deterministic-zero-agent-cicd | 13 | 13 | 100% | 0 |
| Push on main | 12 | 12 | 100% | 0 |
| build-multiarch | 12 | 12 | 100% | 0 |
| portal-app | 12 | 12 | 100% | 0 |
| context-index | 9 | 12 | 75% | 0 |
| ci | 1 | 12 | 8% | 0 |
| ruff-required | 11 | 11 | 100% | 0 |
| agent (auto): LEGION #8745 | 0 | 3 | 0% | 0 |
| agent (auto): LEGION #8746 | 0 | 3 | 0% | 0 |
| agent (auto): LEGION #8742 | 0 | 3 | 0% | 0 |

**All runs on main: 373/960 = 39% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 1; with checks on the first commit: 0; no checks recorded: 1.
**Green on the first push** (one commit, every check passed): 0/0 = no graded pull requests.
Commits per merged pull request: median 6, most 6; needing a second commit: 1/1.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 49 | 59 | 83% | 0 |
| Approve parked runs | 48 | 48 | 100% | 0 |
| Live storefront smoke | 0 | 20 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |

**All runs on main: 111/155 = 72% passed on the first attempt; 0 re-runs.**

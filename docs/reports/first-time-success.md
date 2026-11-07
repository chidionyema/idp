# Delivery: right first time

Generated 2026-11-07T08:53:45Z, window since 2026-10-24 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 79; with checks on the first commit: 79; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 46/79 = 58%.
Commits per merged pull request: median 1, most 2; needing a second commit: 5/79.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| greenlane | 314 | 757 | 41% | 0 |
| merge-when-green | 50 | 51 | 98% | 0 |
| deploy-when-green | 48 | 51 | 94% | 0 |
| lane-feedback | 25 | 50 | 50% | 0 |
| factory-ci | 5 | 5 | 100% | 0 |
| ticket-verification | 0 | 4 | 0% | 0 |
| no-harness-folders | 4 | 4 | 100% | 0 |
| ruff-required | 4 | 4 | 100% | 0 |
| scorecard | 4 | 4 | 100% | 0 |
| context-index | 4 | 4 | 100% | 0 |
| guarded-paths | 4 | 4 | 100% | 0 |
| portal-app | 4 | 4 | 100% | 0 |
| build-multiarch | 0 | 4 | 0% | 0 |
| ci | 4 | 4 | 100% | 0 |
| agent (gemini): LEGION #7777 | 0 | 3 | 0% | 0 |
| estate-watch | 1 | 3 | 33% | 0 |

**All runs on main: 471/956 = 49% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 0; with checks on the first commit: 0; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 0/0 = no graded pull requests.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 69 | 78 | 88% | 0 |
| Approve parked runs | 68 | 68 | 100% | 0 |
| Live storefront smoke | 0 | 22 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |

**All runs on main: 151/196 = 77% passed on the first attempt; 0 re-runs.**

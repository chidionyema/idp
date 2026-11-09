# Delivery: right first time

Generated 2026-11-09T09:55:18Z, window since 2026-10-26 (14 days). Two measures per repository: how many merged pull requests were green on the first push (one commit, every check passed), and how many runs on main passed on the first attempt.

## chidionyema/idp

Merged pull requests: 79; with checks on the first commit: 79; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 46/79 = 58%.
Commits per merged pull request: median 1, most 2; needing a second commit: 5/79.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| greenlane | 321 | 786 | 41% | 0 |
| merge-when-green | 59 | 59 | 100% | 0 |
| deploy-when-green | 58 | 58 | 100% | 0 |
| lane-feedback | 56 | 57 | 98% | 0 |

**All runs on main: 494/960 = 51% passed on the first attempt; 0 re-runs.**

## chidionyema/prospector

Merged pull requests: 0; with checks on the first commit: 0; no checks recorded: 0.
**Green on the first push** (one commit, every check passed): 0/0 = no graded pull requests.

Runs on main, completed, passed on the first attempt (workflows with three or more runs):

| Workflow | First-attempt pass | Runs | Rate | Re-runs |
|---|---|---|---|---|
| PR keeper | 64 | 73 | 88% | 0 |
| Approve parked runs | 63 | 63 | 100% | 0 |
| Live storefront smoke | 0 | 22 | 0% | 0 |
| stale | 14 | 14 | 100% | 0 |
| DNS drift drill | 0 | 14 | 0% | 0 |

**All runs on main: 141/186 = 76% passed on the first attempt; 0 re-runs.**

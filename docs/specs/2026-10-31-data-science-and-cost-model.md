# Data science, machine learning and the cost model: what to formalise, and what is worth using now

Status: DRAFT by the outside consultant, 2026-10-31. Nothing here is built. Numbers marked MEASURED were read this run;
ESTIMATE is arithmetic on a measurement; FOUNDER is the founder's own figure, not a measurement.

## 1. The rule

Machine learning is admitted to a decision only when (a) the baseline rule is measured first, (b) the model beats it by a
stated margin on held-out data, and (c) it has a falsifier that can fail. Below the minimum sample it answers BLIND, not a
guess. Until a baseline exists, the right tool is a count or a rule, which is also what the machine-first tenet prefers.
Models and judges are first-class (tenet T-5), but a model with no baseline is a vibe.

## 2. What the data can support today

- MEASURED (GitHub run history, 300 runs, 12:49 to 13:59 UTC 2026-10-31, a 70 minute window): greenlane 79 runs, 48 percent
  success and 50 percent cancelled, 0 failed; median successful run 1.6 minutes, p90 1.9. `ci` 17 runs, 52 percent success,
  35 percent failed. Every other workflow with 15 or more runs was 76 percent or better.
- MEASURED: **one automated lane, `lane/mutation/ldg-b8a43261685f`, produced 38 of the 79 greenlane runs, 28 of them
  cancelled.** Its recent heads are "Merge branch 'main' into mutation/..." commits: it re-merges main and restarts the
  Greenlane each time main moves, and each restart supersedes the last. That is churn, not failures. It is the first
  place to look for waste, and it needs no model: a rule that stops re-running a lane whose last run is still pending.
- Not usable yet: the 627 session records in `estate-graph/sessions/` are hollow (the asked and answered fields read
  "redacted-by-litellm"), so no model can learn from them. The 70 minute window is too short for any trend; a week of run
  history is the minimum before a forecast of failure is worth fitting.
- First use of data science worth building, in order: (1) the cancellation rule above; (2) a per-lane failure table from a
  week of runs; (3) only then a classifier for "this lane will fail", judged against the table as its baseline.

## 3. The cost model

| line | figure | kind |
|---|---|---|
| Router budget ceilings in AGENTS.md section 11: litellm 3.0, consensus 1.0, vision 0.5 per day | 4.5 per day, 139.5 per 31-day month, inside the 0 to 150 contract | policy, ARITHMETIC |
| MiniMax subscription | about 20 per month now, 50 next month | FOUNDER, 2026-10-28 |
| One new paid infra lane | 25 per month in total, unless a compelling reason is stated with its measured cost | FOUNDER, 2026-10-31 |
| GitHub Actions minutes | free while the repo is public | known plan term, not re-checked this run |
| Actual model spend per provider | UNKNOWN: not collectable from this container | |

ESTIMATE of the risk: greenlane ran about 68 times an hour in the window, at about 1.6 minutes a run, roughly 110 runner
minutes an hour. Extrapolated from 70 minutes, so only an order of magnitude. If the repo ever became private, that rate
would exceed a small monthly free allowance within a day. It is another reason to cut the cancellation churn.

Spend lines the cost model must collect, not assume: tokens and cost per provider per day (MiniMax, DeepSeek, GLM, Kimi,
Codex), CI minutes, and the cost of one landed change. The reward is set from these and from the graded outcomes (ADR 0038),
so a lane that is unmeasured is UNKNOWN and earns neither more nor less.

## 4. Activating autonomous departments

A department is a role with an owner, a metric, a budget and a decider. It is active when the metric is measured by the
spine and its incident has an owner. The Infrastructure department is already PROPOSED in
`docs/decisions/2026-10-30-the-infrastructure-department-and-the-stamped-vision.md` and waits for the founder's signature.
Activation needs, per department: an `estate_health` entry in `catalog/critical-functions.json`, an owner role, a daily budget
line summing under the 150 contract, and a named decider (machine, model or judgment). None are created here; the budget
split between departments is the founder's to rule.

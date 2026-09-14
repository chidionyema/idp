# Demo: the budget gate halts a run and surfaces the best-so-far plan

What you are about to see is `bin/idp-budget` replaying the two fixtures its own `rules.yaml`
row names, with the real output pasted below (this run, on this branch).

## Run it

```bash
cd ~/dev/code/idp
python3 bin/idp-budget --run tests/fixtures/budget/exhausted/session.jsonl
```

The fixture declares a plan, then runs six real tool calls with distinct first words (`git`,
`kubectl`, `curl`, `grep`, `docker`, `aws`) — six branches against a per-goal budget of five.

## What you see

```
FAIL  budget halted at step 7 (branch_budget): budget exhausted for sg1 (5/5). You are spinning. Execute revise_plan, or escalate to a human.
      best-so-far: goal=investigate latency spike subgoals=[sg1] steps=5/5 cost=$0.00/$0.50
```

Exit code `1`, the step the ceiling tripped at, the cause, and the best-so-far plan — never a
claim the run finished.

## Why this is the point

Founder essay, 2026-09-14: "Budget exhaustion -> forced termination -- the agent stops thinking
and executes the best-so-far plan when the budget runs out." This is that forced termination: the
declared goal and subgoal state survive the halt, the run does not.

## The other direction, which matters as much

The same gate lets a run finish clean when it completes its plan inside budget:

```bash
python3 bin/idp-budget --run tests/fixtures/budget/complete/session.jsonl
```

```
ok    budget plan complete inside budget
       goal=restart the stalled worker subgoals=[sg1*] steps=3/5 cost=$0.00/$0.50
```

Three distinct tool calls, then `complete_goal` — the subgoal is marked done and the plan
finishes at 3 of the 5-step ceiling, never touching it.

## Name the cause without acting on it

```bash
python3 bin/idp-budget --explain tests/fixtures/budget/exhausted/session.jsonl
```

```
halted at step 7: branch_budget -- budget exhausted for sg1 (5/5). You are spinning. Execute revise_plan, or escalate to a human.
      best-so-far: goal=investigate latency spike subgoals=[sg1] steps=5/5 cost=$0.00/$0.50
```

Exit `0` always — `--explain` reports, it never fails the caller.

## The honest limit

Three ceilings, deterministic, no model: branch budget (`bin/idp-trajectory`'s own
`budget_per_goal`/`authorize()`, imported not re-implemented — R43), information gain (a
repeated `(tool, target)` pair, the same normalisation `bin/idp-epistemic` uses), cost (a
running sum of each step's own declared `cost_usd`, never fabricated). There is no Bayesian
information-gain engine here — the ticket names that as an open risk, and repeat-vs-novel is the
provable floor this gate stands on, not a stand-in for it.

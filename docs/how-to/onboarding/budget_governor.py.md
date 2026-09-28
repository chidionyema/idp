# How to put the budget gate on a run

The gate replays one recorded transcript against three ceilings and exits 0 (finished or ran
clean inside budget), 1 (a ceiling tripped), or 2 (BLIND — the transcript could not be read). It
takes no configuration and needs no model.

## Run a transcript against the budget

```bash
python3 bin/idp-budget --max-steps 5 --max-cost-usd 0.50 --run ~/.pi/agent/sessions/<project>/<timestamp>_<id>.jsonl
```

Real output on the estate's own exhausted fixture:

```
$ python3 bin/idp-budget --run tests/fixtures/budget/exhausted/session.jsonl
FAIL  budget halted at step 7 (branch_budget): budget exhausted for sg1 (5/5). You are spinning. Execute revise_plan, or escalate to a human.
      best-so-far: goal=investigate latency spike subgoals=[sg1] steps=5/5 cost=$0.00/$0.50
```

Real output on the estate's own complete fixture:

```
$ python3 bin/idp-budget --run tests/fixtures/budget/complete/session.jsonl
ok    budget plan complete inside budget
       goal=restart the stalled worker subgoals=[sg1*] steps=3/5 cost=$0.00/$0.50
```

## Name the cause without acting on it

```bash
python3 bin/idp-budget --explain <session.jsonl>
```

Always exits `0`; prints the ceiling that tripped and the best-so-far plan, or "not halted" if
neither ceiling was reached.

## The three ceilings, evaluated per real tool call, in this order

| ceiling | what trips it |
|---------|----------------|
| information gain | this step's `(tool, target)` pair already ran this session — zero new evidence |
| cost | this step's own declared `cost_usd`, added to the running total, would cross `--max-cost-usd` (default 0.50) |
| branch budget | `bin/idp-trajectory`'s own per-goal `authorize()` refuses — the goal has spent `--max-steps` (default 5) real steps |

`declare_plan`/`revise_plan` bind the run to `bin/idp-trajectory`'s lock; `complete_goal` marks a
subgoal done. Whichever ceiling trips first halts the run; nothing after that step is replayed.

## Exit codes

| code | meaning |
|------|---------|
| 0 | the run finished its plan, or never crossed a ceiling |
| 1 | a ceiling tripped — the run was halted |
| 2 | BLIND — the transcript could not be read, or was not valid JSON per line |

## Prove the script itself runs

```bash
bin/idp-budget --self-test
```

Runs the real budget path against the two fixtures above and exits 0 only if the exhausted one
halts and the complete one does not — the same proof `bin/idp-script-compiles` requires of every
executable under `bin/` (LAW 45).

## What it will and will not catch

**Catches** the founder essay's named failure mode: a run that keeps spending steps or dollars
past its declared ceiling instead of stopping and handing back what it has.

**Does not catch** a run that stays inside every ceiling but pursues the wrong plan entirely —
that is `bin/idp-trajectory`'s and `bin/idp-prm`'s job, not this gate's. It also does not run a
Bayesian information-gain estimate; repeat-vs-novel on `(tool, target)` is the deterministic floor
the ticket's own risk register asks for, not a claim of something richer.

## Adding a rule

The gate is registered in `rules.yaml` as `id: budget` with a fixture pair, so `bin/idp-ci` runs
it and `docs/policy/rules-table.md` is generated from it. Change the rule by editing
`rules.yaml`, then regenerate:

```bash
bin/idp-rules render-agents-md
bin/idp-rules run --only budget
```

# sovereign/shadow -- prediction (W5)

Master Spec v1.0 sections 2.4, 3.2, 3.3, 3.4. Three parts, one package.

| file | what |
|---|---|
| `preauth.py` | R10/R21. Predicts the next `shadow.horizon_steps` steps' spend, surfaces one card, and lets the shadow-founder answer it above `shadow.min_confidence`. `ShadowAuth.op` is typed `NonDestructiveOp`; a destructive op cannot be auto-authorized because no value of that type exists for one. |
| `workflow.py`, `activities.py`, `branching.py` | R19. `BranchParentWorkflow` forks `branch.count` `BranchChildWorkflow` children (Temporal child workflows), each on its own git branch and worktree, each capped at `branch.budget_pct` of the parent budget through `engine/budget.py` (crew#213). Winner fast-forwards into `branch.main_branch`; losers stay as refs; exactly one `branch_merge` receipt. |
| `distill.py` | R18/R20. Frontier successes -> queue + Langfuse dataset (local mirror always) -> LoRA job through `distill.trainer` (ollama or axolotl, subprocess) -> deterministic grade -> route flip at `distill.route_accuracy`, as a `distill` receipt. |
| `cli.py` | `sb branch`, `sb distill`, `sb preauth`; `sb start --branches N` delegates here. |
| `config_keys.py` | every tunable above, merged into `sovereign/config.py` KEYS. |

## Run

    bin/sb start --runner claude --repo <repo> --task 'refactor X' --branches 3 --budget 10000 --json
    bin/sb distill --task-class git_rebase --json
    bin/sb preauth --session-id sb-1 --remaining 10000 --costs 4000,4000,4000 --json

## Prove

    cd sovereign && python -m pytest tests/bdd -q -p no:cacheprovider -k "cp26 or cp27 or cp28"
    cd sovereign && python -m pytest shadow/test_shadow.py -q

cp27 starts a real Temporal dev server from the `temporal` CLI on PATH
(`temporal.cli_binary`) through the SDK's `WorkflowEnvironment.start_local`.

## Residual

The engine's `SessionWorkflow` does not yet call `preauth` before a
transition; the planner is driven by `sb preauth` and the cp26 suite.
Wiring it as an activity in `engine/workflow.py` is W1's file.

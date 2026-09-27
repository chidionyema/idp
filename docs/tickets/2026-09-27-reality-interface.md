# The reality interface: a model's attempt is a hypothesis, the check is reality

**Status:** critical, 2026-09-27. Built by one `claude-sonnet-5` builder through `delegate-build`,
reviewed by the planning session. Tracked on crew#975.

**One sentence:** an agent's failed guess is removed from the tree and from its next prompt, so
the next attempt starts from the instructions and the raw error, never from its own wrong
reasoning.

## The problem

An agent writes "the network is green". If that sentence re-enters its context unverified, the
next turn reads it as fact. The loop is assumption → output → stronger assumption. The founder's
pasted design asks for four laws:

1. **Epistemic segregation.** Dispatcher-written facts sit apart from model-written text.
2. **Context pruning.** A failed hypothesis is deleted, and only the empirical error goes back.
3. **Intent-only output.** An agent cannot state a claim it cannot back.
4. **Three phases.** Hypothesis (model) → execution (host) → verification (deterministic check).

## What already existed (AGENTS.md §6)

| Law | Where it lives | Gap |
|---|---|---|
| 3 | `bin/epistemic_firewall.py`, Stop hook (#4439, #4463, #4472) | none for this ticket |
| 4 | `delegate-build dispatch`: builder acts, `done_check` decides | none |
| 2 | each retry is a fresh `claude -p`, so reasoning is not carried | the failed code stayed in the tree, and the retry prompt grew by appending |
| 1 | — | `results.json` mixed the builder's words (`said`) with the outcome |

## What this ticket changes (`platform/estate/libexec/delegate-build.py`)

- Before a step runs, the dispatcher records the tree's `HEAD` and which of the step's files
  existed.
- After every failed `done_check` (the last attempt included), it rewinds only that step's files:
  it checks existing files back out and deletes new ones. Unverified code never stays in the tree.
- Each retry prompt is built fresh from the step's instructions plus one `[EMPIRICAL_STATE]`
  block, which holds the check command, its exit code and its output. The failed attempt's reply
  never appears in any prompt.
- `results.json` now keeps `empirical` (dispatcher-written, one row per attempt with `check_rc`
  and output) apart from `scratchpad` (the builder's words, labelled unverified). The progress
  line prints `check_rc`, never the builder's words.
- `attempts=` (default 3) on the intent.

## What it deliberately does not do

**No history rewriting in the gateway (litellm-local :4000):**
- The `claude-*` lane is append-stable, so the prompt cache stays valid (`efficiency_gateway`).
- Claude Code owns its own conversation.
- Removing a `tool_use` turn without its `tool_result` breaks the Anthropic API's pairing rule.

Pruning belongs in the loop that owns the attempt, and here that loop is `delegate-build`.

## First run, and why the check was widened

The first dispatch passed its done-check and was **rejected in review**. `delegate-build.py` had
never been committed to main. The builder's worktree, cut from `origin/main`, had no file to edit,
so the builder wrote a new one. That rewrite dropped `--model`, the `plan` verb, validation, waves
and parallelism. The done-check tested only the new behaviour, so it could not see what was lost.

Fixes:
- The installed `delegate-build` was committed as the base (`d9a9b2f7`).
- The done-check now also requires that `--model claude-sonnet-5` reaches the builder, and that
  `cmd_plan`, `validate`, the wave pool, `--allowedTools` and the planner/builder args survive.
- It fails at the base (rc 5) before the builder runs.

Lesson: a done-check must guard what must not change, not only what must.

## Done

- `tests/estate/test_delegate_build_reality.py`: with a fake `claude`, a wrong first attempt is
  rewound (`a.txt` back to base, the new file gone) before attempt 2, attempt 2's prompt holds
  `[EMPIRICAL_STATE]` and not attempt 1's words, and a step that never passes leaves the tree at
  base after 3 attempts.
- Operating = installed to `~/.estate/libexec` after merge, and a real dispatch whose
  `results.json` shows `empirical` and `scratchpad`.

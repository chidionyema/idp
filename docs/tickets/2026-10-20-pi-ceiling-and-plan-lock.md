---
id: 2026-10-20-pi-ceiling-and-plan-lock
title: "pi agents exceed the 200k input ceiling and run without declaring a goal"
status: IN_PROGRESS
priority: P1
owner: claude
created: 2026-10-20
---

# Why

Two reports about pi agents on this estate:

1. pi agents consistently exceed the per-call input ceiling (200,000 tokens, set in
   `litellm-local`, enforced by `platform/llm/request_ceiling.py`).
2. Agents are not required to declare goals and sub-goals.

# What was measured (2026-10-20)

- Router: key `laptop-20260829T143252Z` sent 439 calls / 86,525,924 input tokens in 60 min; the
  largest single call was 737,169 in. `spend-breaker-digest.yaml` grades the hourly total at
  2,000,000 and only warns.
- pi resolves every estate model to `contextWindow=128000` (`pi --list-models`), so its own
  compaction trigger is not aligned with the router's 200,000. Compaction was observed firing at
  `tokensBefore=368,926`.
- pi checks "should I compact" only after an assistant message completes. One `estate_execute`
  result was 1,411,712 characters, and the next call carried all of it. No post-turn compaction
  can stop a single turn that large.
- The router's refusal text matched none of pi's `OVERFLOW_PATTERNS`, so pi classed the 400 as an
  ordinary error, did not compact, and re-sent the same history.
- pi has no `declare_plan` tool, so the grader printed `goal=(none declared)` for every pi
  session. The grader already reads pi's transcript shape (`_tool_input`, `_unwrap` in
  `bin/trajectory_lock.py`); nothing existed to call.

# What this change does

| Bug | Change | Test |
|---|---|---|
| refusal unrecoverable | `request_ceiling.py` refusal now says "exceeds the maximum context length of N tokens", which pi's detector matches | `tests/test_request_ceiling.py::test_pi_classifies_the_refusal_as_a_context_overflow` |
| unbounded tool results | `extensions/pi-plan-lock` caps any result over 100,000 chars to head + tail and spills the full text to `~/.pi/agent/state/overflow/` | `plan.test.ts`, `tests/test_pi_plan_lock.py` |
| no goals | same extension registers `declare_plan` / `revise_plan` / `complete_goal` and blocks every other tool at `tool_call` until a valid plan (goal + >=1 sub-goal) exists | `plan.test.ts`, smoke test against a fake pi |
| rollout | `bin/pi-plan-lock-install [--check]` copies the extension to `~/.pi/agent/extensions/pi-plan-lock/` | `tests/test_pi_plan_lock.py` |

Opt-out for a human-driven session: `ESTATE_PLAN_LOCK=off`. The extension fails open on its own
errors, with a notification.

# Not done / open

- **Root cause of the 128000 window is unresolved.** `models-store.json` has `contextWindow`
  entries of 200000 and 204800, but they do not reach the resolved estate models
  (`provider-composer.js` defaults to 128000 when the definition omits it). Both
  `~/.pi/agent/models.json` and `models-store.json` were written 20 Oct 07:49 and no writer was
  found in the repo. Until the estate model definitions carry `contextWindow: 200000` (or a
  lower, deliberate value), pi compacts against the wrong number. The result cap and the
  recognisable refusal bound the damage; they do not fix this.
- **Not yet installed on the live machine.** Run `bin/pi-plan-lock-install` after merge, then
  start a new pi session. Live sessions loaded their tool list before the extension existed.
- **Not tested inside a real pi session.** Verified with pi's own `jiti` loader against a fake
  `ExtensionAPI`; the `tool_result` return shape (`content`/`details`) is taken from the
  extension API as I read it, and a live session is the check that it is honoured.
- The hourly spend breaker still only warns. Severing on it is a separate decision.

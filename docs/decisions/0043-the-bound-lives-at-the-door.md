# 0043 — The bound lives at the door

- **Date:** 2026-10-25
- **Claim:** idp#7118 · agent `pi`
- **Gate:** `bin/timeout-budget` (rung 1f of `bin/idp-ci`)
- **Proposal page:** `docs/timeout-budget.html` — the same argument for a reader who will not open the tree

## Context

Three numbers bounded the same work, and none of them knew about the others:

| where | what it was | what it did |
|---|---|---|
| `mcp/plugins/estate_executor.py` | `CEILING_SEC = 100` | kills the job. The only number that actually binds |
| `platform/estate/bin/estate-execute` | `int(step.get("timeout", 120))` | per-step default **above** the ceiling, so it could never fire; the literal made the door's number invisible in the script's own story |
| `platform/estate/intents/*.yaml` | 24 step `timeout:` lines across 17 intents, plus `timeout N` inside step commands | guesses about how long someone else's work takes |

The intents also declared doors nothing grants: `door_s: 170` in `lane-submit` (170 = 60 + 100 + 10),
`door_s: 300` in `git.commit-staged`, `door_s: 120` in `site-onboard`. The MCP door carried a
`timeout = int(args.get("timeout", 55))` of its own — a second opinion 45 seconds *below* the
executor's, which would have killed `bin/idp-ci`'s 57s schema rung and reported the work as a
timeout.

Two failures, both measured, both in this class:

1. **2026-10-22.** `lane-submit`'s push ran behind `timeout 50` inside a 60s step. The push took
   longer, the step was killed at 60036ms, and `git ls-remote` reported the lane ref **absent** — so
   the estate was told the submission had failed while the push was still landing.
2. **2026-10-25.** The bound was raised to `timeout 80` inside a 100s step. The same push, with the
   estate's pre-push guard attached, took **98s**. Same false failure, one number larger.

A guessed bound cannot be right more often than the distribution it guesses about, and where it is
wrong it is wrong in one direction only: it invents a failure. That is the defect class, and raising
the number is not a fix — it is the same fix applied twice.

## Decisions

**D1. One budget per intent, declared once, in the field the door reads.**
`door_s:` is the intent's budget in seconds. `timeout:` at the top level is the deprecated alias,
still honoured so no live intent breaks mid-migration, and refused on new work by the gate. Absent,
the budget is `CEILING_SEC`, imported from `mcp/plugins/estate_executor.py` — never restated.

**D2. A step may narrow the budget, never widen it.**
`estate-execute` clamps a step `timeout:` to the budget, says `INERT BOUND` when the step asked for
more, refuses a non-integer, and times out with `TIMEOUT (Ns of a Ms budget from door_s)` so the
number that killed the job is always the number the reader can find in one place. A step cap is
legal only when it *splits* a budget between sequential jobs (lane-submit: 40 + 50 = 90 inside 100).

**D3. Eradicate the inner bounds, per bound, judging each.**
All 24 step `timeout:` lines and the three over-ceiling `door_s` declarations are gone. `lane-submit`
keeps 40/50 because those split one budget between two jobs; nothing keeps a bound that guessed a
duration. Where the old bound existed to guarantee a *measurement* ran after a push (the #5814 fix),
the mechanism replaces the guess: the push runs in the background and the step bounds only its own
observation of the remote ref. A bound on the measurement cannot truncate the work. When the push
outlives the window the step says `IN-FLIGHT` with the pid and the verdict command — it does not say
`absent`.

**D4. A probe may be bounded below the work it guards, and must say why.**
`timeout 2 curl -sf .../health  # estate:bound the service must fail fast, not hang the step`. The
marker without a reason is not a marker; the gate refuses one.

**D5. The MCP door's child bound is derived, not restated.**
`CHILD_BACKSTOP_SEC = DOOR_CEILING_SEC + 15` (process start and teardown). It cannot undercut the
door, and it cannot drift from it, because it is the same number plus a fixed allowance.

**D6. Enforce it with a ratchet, not a wall of prose.**
`bin/timeout-budget` fails on: a `door_s` above the ceiling; steps whose declared caps sum past the
budget; a step cap wider than the budget; a literal bound inside an intent command (strict); and a
new literal bound in `bin/` or `hooks/`. When the gate was switched on, `bin/` carried 12 bounds and
they were recorded in `bin/timeout-budget.baseline` — shipping mode, because a strict gate would have
been red before any lane touched anything, and a gate every lane must bypass is not a gate.

**The ratchet is empty in the same lane (2026-10-25).** Judged one bound at a time rather than
stripped: six were deleted and six marked.

| Bound | Judgement |
|---|---|
| `timeout 240` ×2, `timeout 300` ×3 in `bin/estate-security-scan` | **deleted.** Larger than the door that runs the script, so it could never fire inside the estate and only ever turned a hang in CI into an empty advisory list — a false "clean" |
| `timeout=120` on a local `git ls-files` in `bin/treewalk.py` | **deleted.** Above the ceiling, and a bound on work can only truncate it |
| `timeout=30` on one `gh api` round trip (`lib/receipt_age.py`, `lib/ledger_fresh.py`) | **marked** `# estate:bound <why>` — a hang there is a no-answer, not 30s of work |
| `timeout=30` on one registry verify URL (`lib/vendor_verify.py`), `timeout=20` on one emit (`lib/conscience_emit.py`) | **marked** — one HTTP exchange, shorter than the work it sits inside by design |
| `timeout=10` on a TCP connect (`redteam_promoter/promoter.py`), `timeout=30` on one child script (`reasoning_gateway_hook.py`) | **marked** — a connect, and a hook that must not block the harness |

`bin/timeout-budget --strict-ratchet` is therefore green on the tree, and it is rung 1f of `bin/idp-ci`.
The baseline may only ever shrink; the day a new bound is needed, the honest move is the marker, not
a baseline line. The gate's own tests grade it by feeding it trees it must refuse.

**D7. The gate grades the library an agent invokes, not only the checkout.**
`~/.estate/intents` is main's 96 intents **plus ~266 crystallized on this laptop that exist nowhere
else**, and `estate-runtime-sync` only ever adds or updates it — it never deletes. Measured
2026-10-25: that library carried **133 step caps across 116 files, 57 of them at or above the
ceiling**, plus three top-level `timeout:` declarations of 600s, 600s and 180s — time no door
grants. A gate that graded only the checkout would have reported the estate clean while every
agent on the machine ran inside a guess. The eradication therefore ran twice: the repo library in
the commit, and the installed library on the machine (backed up first, to a tarball). The installed
scope is strict and machine-local; on a machine with no `~/.estate/intents` — CI — the gate says
`checkout only` and grades what it can see.

## What this changes about how the estate is read

A wall-clock number in an intent is now a claim about the *budget*, not about the work. If a step
needs longer than the door allows, the answer is the session plane (`estate_session_start`), not a
larger literal. The end state is here, not promised: the ratchet is empty, so every surviving number
in the tree is either the door's own or a marked probe.

## Consequences

- **The eradication also ran on the machine.** `~/.estate/intents` is main's intents plus ~266
  crystallized here that exist nowhere else, and runtime-sync never deletes. It carried 133 step
  caps (57 at or above the ceiling, so inert) and three top-level declarations of 600s, 600s and
  180s. All were removed — 131 caps from 116 files, the three declarations, and three deprecated
  `timeout:` fields renamed to `door_s` — after a backup. `lane-submit` keeps its 40/50 split, and
  the live copy of `estate-execute` and `lane-submit` was installed from this branch so the lane
  could submit under the new doctrine rather than the old one.
- `lane-submit` no longer declares 170s of work inside a 100s door: it declares 100 and spends
  40 + 50 inside it. Its `hand it over` step is folded into the push step, where the ref is already
  read; a slow push is reported as in flight, and the verdict is read from the `greenlane` commit
  status rather than held open for.
- A step that outlives the door is now killed by the door's number only, so the error names the
  budget and its source.
- The 12 ratcheted bounds in `bin/` are visible rather than invisible: `bin/timeout-budget` prints
  them, and `--strict-ratchet` fails until they are gone.

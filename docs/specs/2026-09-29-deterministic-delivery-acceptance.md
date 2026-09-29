# Deterministic delivery — the acceptance criteria (uncompromising)

Founder, 2026-09-29. This is the contract for how work reaches main and production on this
estate. It is short on purpose. Every line is an **invariant** with its **mechanism** (what
refuses a violation, in the environment, not in an agent's judgement), its **measurement**
(the number that proves it, read live) and its **surface** (where the founder sees it without
asking). "We already have this" is not a state; a green measurement is.

A control that cannot be shown failing red on a bad input and passing green on a good one does
not exist. A control an agent can edit, extend with an `if`, or route around does not exist.
A step that needs a human to run a command is not a pipeline.

## I1. main is never red

- Invariant: at every instant, every required check on `main`'s head commit is green, and
  `main` can be released from.
- Mechanism: exactly one writer of `main`, the Greenlane engine (`greenlane/engine.py`,
  `.github/workflows/greenlane.yml`), acting as the estate GitHub App; the `idp-main-writer`
  ruleset lets only that App update `main`. The engine fast-forwards `main` only to a
  candidate sha whose required checks are already green **at that sha**. There is no other
  path: no merge button that lands, no bot that merges, no push by a person or agent.
- Measurement: `bin/idp-greenlane status` → `invariants.main_green` (required-check
  conclusions on `main`'s head). Red for one second is a P0 bug in the mechanism, never
  "flaky".
- Surface: `/fleet` greenlane envelope; `alarm: true` the moment it is false.

## I2. no pull request can be red

- Invariant: a pull request exists only when its sha has already been proven green on top of
  the current `main`. Agents cannot raise one.
- Mechanism: agents push `lane/<name>` (`estate-execute lane-submit`) and stop. The engine
  builds the candidate, grades it, then raises the PR itself and lands it in the same move.
  A hand-raised PR is closed and relaned by the engine within one tick. The repository
  owner's own PR is exempt (the founder's landing vehicle for I6).
- Measurement: `invariants.open_prs_not_raised_by_engine == 0`, `red_open_prs == 0`.
- Surface: `/fleet` greenlane envelope.

## I3. no work in the void

- Invariant: every commit an agent pushed is, at every instant, on `main`, on its lane, or on
  its branch, and its verdict (`landed | testing | red: <reason> | conflict: <reason>`) is
  readable. A closed PR is never the end of anything.
- Mechanism: the engine never deletes a lane it did not land; a red or conflicting lane keeps
  its branch and carries the reason on its head's `greenlane` commit status; relaning
  comments the lane name on the closed PR.
- Measurement: `invariants.work_lost == 0` (closed-unmerged PRs whose commits are on no
  branch, no lane and not in `main`); per-lane status in `state.lanes`.
- Surface: `/fleet` greenlane envelope; an agent asks `lane-status` (intent), never a PR
  page.

## I4. landing is atomic and deterministic

- Invariant: a green candidate lands within one tick of turning green; a red candidate is
  bisected, and only the culprit lane is marked red; `main` moving under a candidate requeues
  it, never lands it stale; the engine survives restart at any point with no lost state.
- Mechanism: batching + bisection in `greenlane/engine.py`, state in `refs/greenlane/state`,
  one concurrency group, idempotent ticks.
- Measurement: `features/gates/greenlane.feature` under 500 chaos lanes × 3 seeds
  (`sovereign/tests/bdd/test_greenlane.py`): main never red, nothing but the engine moves
  main, no work lost, every truly-green lane lands, restart every tick. This suite is a
  required check; it fails, nothing lands.
- Surface: candidate, batch id, landed_total in the greenlane envelope.

## I5. deploy is part of landing

- Invariant: a landing that changes a deployable is not complete until Flux has applied it and
  the service emits a real production log line; otherwise the landing is reverted like a
  transaction abort. "Merged but never ran" is a forbidden resting state.
- Mechanism: Flux row per deployable with `wait: true` (never `wait: false`); the deploy
  proof step in the lane reads the Flux ledger and the service's log through an intent
  (`k8s-logs`) and reverts on timeout.
- Measurement: per-landing deploy receipt; `flux_not_ready == 0` for rows the landing
  touched.
- Surface: `/fleet` CI/CD channel.

## I6. agents do not change the enforcer

- Invariant: `.github/workflows/**`, `platform/github/ruleset.*.json`, `bin/repo-rulesets`,
  `.githooks/**`, `greenlane/**` change only through a PR authored by the repository owner.
- Mechanism: the engine refuses any lane whose diff touches those paths (verdict
  `refused: enforcement path`); the ruleset allows no one but the App to update `main`, and
  the App only ever fast-forwards to a graded candidate. The founder's PR is the one path.
- Measurement: count of enforcement-path changes on `main` not authored by the owner == 0.
- Surface: refused lanes in the greenlane envelope with the reason.

## I7. no founder-manned steps, no silent failures

- Invariant: nothing in this pipeline asks a person to run a command. Anything the pipeline
  cannot do for itself is a **pending approval** on the founder's surface
  (`~/.estate/intents/pending/`, `estate_pending`), never an instruction in a chat.
  Every failure of the pipeline itself (token, permission, quota, network) is a visible red
  on `/fleet` within one tick, with its reason.
- Measurement: greenlane workflow run conclusions; `BLIND`/`REFUSED` lines in the tick log
  surface as `alarm`.

## I8. one estate, no harness silos

- Invariant: no repository contains a `.claude/` (or any harness-named) directory; no estate
  code reads or writes under `~/.claude` or any harness home; every agent, whatever model or
  harness, gets its knowledge from the same places — `AGENTS.md`, the growmos graph, the
  unified memory server, `~/.estate`, crew — and records its actions in the same place — the
  signed action ledger on `estate.agent.>`.
- Mechanism: pre-push Layer 0 and a CI test refuse any commit whose *paths or contents*
  name a harness home; a local converger (`platform/estate/libexec/claude-silo-converge.sh`,
  run by `idp-disk-watch` every 5 min) quarantines anything that regrows; ported capabilities
  (session ledgers, directive mailbox, guards) live under `~/.estate/state`.
- Measurement: files naming a harness path in estate code == 0; `~/.claude` holds only the
  harness's runtime state; `<repo>/.claude` does not exist.
- Surface: `/fleet` memory channel.

## What "done" means for any change to this pipeline

1. The invariant it serves is named (I1–I8).
2. The mechanism is shown **red** on a violating input and **green** on a good one, in the
   test that CI runs by default.
3. The measurement is read live after landing and quoted with its value.
4. The founder can see it on `/fleet` without asking.

Anything else is narration.

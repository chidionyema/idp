# Onboarding: estate-state-grader

## What it is

`bin/estate-state-grader` turns an estate snapshot (`STATE.md`) into a clean
per-row ledger and a roll-up of the rows that need a human. It is slot 2 of the
seven-agent local ops tier (crew#929, roster in
`docs/ops/local-ops-tier-roster.md`).

## Why it exists

The daily snapshot is a long table of service state, and reading it is exactly
the kind of recurring work a 24/7 worker should absorb: skimming ~50 rows to
answer "what is red, what was never measured". A grader that reports the RED /
NOT RUN rows with their reason removes that scan and keeps the answer
deterministic and auditable.

## The rubric

A row grades:
- **GREEN** only on an explicit pass signal (`GREEN`, `MEASURED_OK`, `OK`);
- **RED** on `RED` / `FAIL` (or a RED/FAIL sub-detail);
- **NOT RUN** on `NOT RUN`, `UNKNOWN`, or an empty/unmeasured cell — a row the
  snapshot could not measure is never turned into a guessed pass;
- **UNKNOWN/INFO** for a partial or count-only cell that carries no verdict.

## How to run it

- `bin/estate-state-grader` — grade the sibling crew `STATE.md` (override with
  `ESTATE_STATE_FILE`).
- `bin/estate-state-grader /path/to/state.md` — grade any snapshot file.
- `cmd | bin/estate-state-grader -` — grade snapshot-shaped rows on stdin.

## The contract

The grader reports measured state only. A count row or an unmeasured cell is
kept visibly unresolved (NOT RUN / UNKNOWN), never elevated to green. This is
the LAW 2 discipline applied to daily state: the ledger names what is down and
what is unknown, and nothing is claimed without a measurement behind it.

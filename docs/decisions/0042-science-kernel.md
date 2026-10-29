# 0042. The science kernel: preregistered programmes, immutable evidence, independent verification

Status: accepted (2026-10-29). Claim: chidionyema/idp#7372.

## Context

`platform/science` holds one CronJob (`science-facts`) that counts telemetry rows per source. It
measures that the science *collector* is alive; it does not run, verify or record any experiment.

## Decision

`packages/science` is the one place a scientific programme is registered and judged.

- A programme is a frozen protocol (question, hypothesis, null, falsifier, metric, analysis plan,
  fixture digest, verifier, budget, risk tier). Production experiments are refused.
- State moves only along `proposed -> preregistered -> running -> analysed -> independently_verified`
  (or `rejected`, then `archived`). Each move and its evidence row commit in one `BEGIN IMMEDIATE`
  transaction with compare-and-set on the state, so a lost race leaves no orphan row.
- Evidence and the protocol are immutable by SQLite trigger, not by convention.
- The experimenter is the actor logged on the move to `running`; the caller cannot name them.
  Verification needs a different actor, a sha256 receipt, and a cited `audit` or `replication` row.
- `science.cycle` runs one programme with no human step; the verifier recomputes from the ledger's
  raw measurements, never from the experimenter's summary. Scheduled as `ai.estate.science-cycle`.

## Trade-offs

SQLite WAL gives one writer at a time: fine at one cycle a day, wrong for high-throughput ingest.
The scheduled fixture is frozen, so the daily run proves the kernel's autonomy and integrity, not a
new scientific finding; real programmes register their own protocol and fixture.

## Retirement of the old lane

`platform/science/science-facts.yaml` is not replaced by this change: it is observability of the
collector and stays until it is folded into a Dagster schedule per `one-scheduler.yaml`. No
research function of the old lane is left to retire: it never ran an experiment.

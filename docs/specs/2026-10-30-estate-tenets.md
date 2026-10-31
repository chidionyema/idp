# Estate tenets: structure first, each one measured and each one checked

**Date:** 2026-10-30 | **Claim:** [idp#7493](https://github.com/chidionyema/idp/issues/7493) | **Status:** proposed

## Why

The founder asked for reusable, parameterised intents and functions, structure before free text,
and an oracle that finds anything across the estate in one pass. A tenet that nothing enforces is
the same looseness it criticises, so every tenet below names its **measurement** and its
**check**, and says `UNENFORCED` where no check exists yet.

## Builds on, does not replace

[context broker decision](../decisions/2026-10-27-the-estate-context-broker-is-the-only-door.md) |
[compiler and gateway](../decisions/2026-10-26-one-context-compiler-and-one-execution-gateway.md) |
[one memory plane](../decisions/0050-one-memory-plane-and-it-is-cortex.md) |
[context plane reference](../reference/estate-context-plane.md) |
[agent surface map](../reference/estate-agent-surface-map.md) |
[constrained formats research](../research/2026-10-25-constrained-formats-research.md) |
issue #7344 (the context-substrate programme, strictly ordered, P0 first).

## Tenets

| # | Tenet | Measurement | Check | Status |
|---|---|---|---|---|
| T1 | Reuse before create: an intent or function is added only when `bin/capability-index` finds no fit | share of `estate_list` lookups followed by a create | none | UNENFORCED |
| T2 | An intent's args are declared, typed, described; no undeclared `{{var}}`, no raw `<<var>>` | `bin/schema-conformance intents` (R0 to R4) | `tests/test_schema_conformance.py`; **not wired into CI** | PARTIAL |
| T3 | An intent declares its output shape | 358 of 362 installed intents declare none (2026-10-30) | none | UNENFORCED |
| T4 | An intent describes itself in a sentence a stranger can act on | 190 of 362 descriptions under 40 chars | none | UNENFORCED |
| T5 | No hardcoded user path in an intent | 205 of 362 installed intents contain `/Users/` | none | UNENFORCED |
| T6 | Where a schema fits, free text is refused | constrained-formats baseline (74 violations over 96 committed intents) | `bin/schema-conformance --baseline` | PARTIAL |
| T7 | Every answer about the estate carries source-linked citations, abstains without evidence, and says UNMEASURABLE where no reader exists | `eval/estate-context/gate_seed.py` | `tests/estate/test_context_seed_gate.py` (17 tests, mutation-checked) | ENFORCED for the seed set only |
| T8 | A probe that cannot be measured is BLIND, never a quiet PASS | critical-watch idiom | `tests/estate/test_critical_watch.py`, the seed grader | ENFORCED |
| T9 | Discovery is adapters behind the one broker, never a second index | decision 2026-10-27 | none | UNENFORCED |

The counts are for the **362 installed** intents in `~/.estate/intents`, which git does not track;
the tracked set is the 110 files in `platform/estate/intents`. The next lane must measure the
tracked set, because that is the one CI can check.

## Discovery: the design after consulting codex (2026-10-30)

Codex reviewed the proposal from the facts above. What it concluded, and what this spec does about it:

1. **Adapters behind the broker, not a new door.** Registry entries are contracts and source
   identifiers, not indexed content. Code stays with gortex, memory with unified-memory-server.
   Taken: T9.
2. **Observation states differ from evaluation verdicts.** `ABSENT`, `READER_UNAVAILABLE`,
   `ACCESS_DENIED`, `STALE`, `UNMEASURABLE` describe a source; PASS/FAIL/BLIND grade a check. The
   seed uses `abstain` (no evidence exists) and `unmeasurable` (no reader) for the first two.
3. **Unresolved conflict, for the founder or #7344's owner:** the broker requires a live claim,
   and the founder ruled on 2026-10-27 that gathering context needs none. Read permission and
   landing permission must be separated before any federated reader ships.
4. **Path.** Codex advised `eval/estate-context/**`, the programme's own directory, over a new
   one. Taken; the first draft's `eval/estate-discovery/` is dropped.
5. **Defer.** Intent structure checks are separate work and must extend `bin/schema-conformance`
   rather than add a second linter. Taken: goal_15 is its own claim.

Codex's first attempt failed: the estate's own `estate-execute` needs a writable database, and a
read-only sandbox cannot open a ticket. That is itself a finding: an agent whose reader is
refused must report `READER_UNAVAILABLE`, not conclude the source is empty.

## Source types the oracle must cover, and the reader that exists

| Source | Reader in the repo today |
|---|---|
| Code | gortex via `bin/estate-context-compile` and the broker |
| Specs, decisions, reference, runbooks | none for content; `bin/estate-spec-status` for proof status |
| Issues and CLAIM comments | the broker's per-path claim check only |
| Memory facts | `platform/estate/memory/door.py` |
| Sessions and agent activity | `bin/estate-session-recorder` writes; no query reader |
| Capabilities and intents | `bin/capability-index` |
| Schedulers, launchd, CI | none |
| Ledger | none |
| Cluster | `bin/idp-inventory`, `critical-watch.py`; unreachable from the laptop (#7343) |

"None" means none was found by a name search of `bin/` and `platform/estate/`; it is not proof of
absence. Each adapter, when built, needs its own freshness probe.

## What this lane ships, and what it does not

Ships: this spec, the seed set (10 questions, 6 answerable, 1 abstain, 3 unmeasurable), the
grader, its tests. Does not ship: the 100-question set (#7344 P0), any broker change (P3), any
intent ratchet (goal_15), or the CI wiring for T2.

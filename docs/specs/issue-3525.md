# Build: The Battalion — asymmetric compute-cost leverage (spec v0.1)

Issue: https://github.com/chidionyema/idp/issues/3525
Written by pm-agent on 2026-09-15 from conversation with @chidionyema333@gmail.com.

## What the founder asked for

Spec (frozen pending sign-off): `docs/specs/2026-09-15-asymmetric-compute-leverage-spec-v0.1.md`.
Founder, verbatim, on scope: "the answer to 99% of the questions is we need everything and the
seamless ability to enable/disable every axis of the full matrix configuration, and once
configured it needs to be super intelligent, and needs uncommon and rare product-design and
systems-engineering skill" and "so all options in one super intelligent super configurable
battalion — that's how we squash this problem forever" and "nice UX design for all edge cases,
must be as seamless and reliable as electricity." This issue does not re-litigate the spec; it
tracks building exactly what it already specifies, REQ by REQ, checkpoint by checkpoint. One
checkpoint per major REQ group in the spec, plus the three P0 prerequisites it names as
load-bearing for every other claim in it.

Infra facts (`bin/idp-ticket-facts llm`): posted verbatim on the issue thread (crew#629 CP2) —
never retyped here. Every checkpoint below lives on the `llm` Backstage component (namespace
`llm`, front door `llm.mumchimp.com`) — OBS-01 requires the hosting matrix and the CFG-01 config
surface to both be generated catalog entities on that same component page, not a bespoke
dashboard, so every "Door" below is a link this build adds to that one page, never a new one.

## Checkpoints

### CP1: Cost & spend governance (COST-01..04) — hard severing breaker, hardware-signed paid-compute activation, versioned breakeven-gated cost ladder, graded cost table

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Budget & breaker** link ->
shows breaker state (armed/severed), the current cost-ladder rung, and the graded cost table
with its receipt-grade column.

Verified by `@cp1` in `features/`.

### CP2: Compute provisioning / JIT (JIT-01, JIT-02) — point-of-use tiers honoring Apple 24h floor vs GPU per-second, cold-start budget with declared degradation

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Compute tiers** link -> each
tier row shows its activation_floor (24h for Apple Silicon, per-second for GPU) and declared
cold-start latency budget.

Verified by `@cp2` in `features/`.

### CP3: Routing & escalation (ROUTE-01..06) — model-agnostic router only, the tier x volume x selection x escalation matrix as independent config-toggleable axes, verifier-driven and disagreement-driven escalation, local-model floor termination

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Routing matrix** link -> each
of the four axes (resource tier, candidate volume, selection method, escalation pattern) shown
as its own toggle, with config_id linking through to the Langfuse trace query.

Verified by `@cp3` in `features/`.

### CP4: Verification & selection (VER-01..04) — the three-stage gauntlet, selection method as a strategy slot, claim-graph as NL verifier, volume capped where no real verifier exists

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Verifier gauntlet** link ->
shows the three stages (structural/Z3/execution) with pass state, and the claim-graph
NL-verifier verdicts for the same run.

Verified by `@cp4` in `features/`.

### CP5: Offload, grind, darwin, orchestration (OFF-01/02, GRIND-01, DARWIN-01, ORCH-01..03) — deterministic ops never spend a token, CPU sandbox gap, unkillable overnight grind, confirmed-or-gap weekly meta-optimizer, Temporal-only orchestration, time-boxed flat-rate volume, config_id on every trace

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Orchestration** link -> opens
the Temporal Web UI filtered to this component's child workflows (grind worker, darwin
optimizer), same door as the existing `branching.py` workflows use today.

Verified by `@cp5` in `features/`.

### CP6: Free-lunch invariants (FL-01..04) — speculative decoding, exact-match cache safeguards, trace tagging, weighted verifier voting are the only claims allowed to call themselves free

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Cache & speculative decoding**
link -> shows the draft-model rejection-sampling guarantee, and the exact-match cache's TTL +
opt-out + reuse-marked-in-trace fields together, so a broken safeguard is visible, not silent.

Verified by `@cp6` in `features/`.

### CP7: Configuration surface CFG-01/CFG-02 — one hot-reloadable config document is every axis's single point of control, no redeploy; its schema is generated from this spec's own REQ list so a REQ without a schema field fails CI

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Battalion config** link -> the
single CFG-01 document, rendered field-by-field with its current values and version number;
each field traces back to the REQ that named it.

Verified by `@cp7` in `features/`.

### CP8: Observability & delivery (OBS-01, OBS-02, GOV-01, GOV-02) — hosting matrix and CFG-01 surface as generated catalog entities, founder deliverables on the estate's own board, zero laptop dependency in the routing path, money-spending autonomy inherits the destructive capability class

Door (from the UI): Backstage -> Catalog -> `llm` component page itself, plus the founder board
at `127.0.0.1:8787` -> `/look` — this checkpoint is the two doors above existing at all,
generated rather than hand-built, and nothing in the routing path resolving to founder hardware.

Verified by `@cp8` in `features/`.

### CP9: UX & reliability bar (UX-01..03) — identical response shape across every config cell, every enumerated edge case has a tested degradation path, the local floor lane is schema-enforced un-disableable

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Edge-case matrix** link -> each
enumerated edge case (cold-start overrun, mid-request eviction, budget breach, verifier timeout,
all-lanes-down, hot-reload mid-request, disable-all-lanes attempt) shown with its degradation
test's pass state.

Verified by `@cp9` in `features/`.

### CP10: P0 prerequisites (P0-01..03) — the severing breaker, the CFG-01 config document, and the UX-02 edge-case suite each exist and pass before any "hard-metered", "seamless matrix", or "reliable as electricity" claim is made

Door (from the UI): Backstage -> Catalog -> `llm` component -> **Battalion readiness** link ->
three fields, one per P0 (breaker severs / CFG-01 document exists / edge-case suite green), each
red until its own test passes — this is the gate the other nine checkpoints' claims stand on.

Verified by `@cp10` in `features/`.

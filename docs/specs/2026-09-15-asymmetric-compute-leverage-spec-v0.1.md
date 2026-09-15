# Asymmetric Compute Leverage — Spec v0.1 ("the Battalion")

**Naming directive (2026-09-15, mid-turn):** "so all options in one super
intelligent super configurable battalion — that's how we squash this problem
forever." This spec is not a menu of separate features; it is the design of
ONE system — the Battalion — where every tier, axis and mechanism below is a
config cell inside it (CFG-01/CFG-02), not a standalone tool someone picks
between. "Squashing the problem forever" means: once this ships, no future
compute-leverage question gets answered by more bespoke scripts or a new
one-off integration — it gets answered by a config edit to the Battalion.

Status: PROPOSED — frozen on founder sign-off. After freeze, changes require
a version bump + diff against this file. Purpose: every instruction repeated
across the 2026-09-15 session is stated once here, made testable, and made
complete by construction (traceability coverage is a mechanical check, not a
vibe).

**Founder directive resolving the open decision register (D1-D6, §7):** "the
answer to 99% of the questions is we need everything and the seamless ability
to enable/disable every axis of the full matrix configuration, and once
configured it needs to be super intelligent, and needs uncommon and rare
product-design and systems-engineering skill." This overrides any
partial-scope default below: every axis in §3's ROUTE-02 matrix, every tier
in COST-03's ladder, and every mechanism in §5/§6 SHALL ship as a live
enable/disable toggle in the same config surface, not a subset picked by an
agent's judgment. D1-D4/D6 stand as stated (they're research-sourcing
questions, not scope questions); D5 (do-calculus/refinement-type DSL) is
explicitly NOT deferred by this directive — it stays out of v0.1 only because
nothing in the repo implements it yet, not because it's out of scope; it is
the first thing added once GRIND-01/DARWIN-01 land.

Conventions: SHALL = mandatory, verifiable. Every REQ has: source (S#),
acceptance test, verification method. Nothing enters build without a REQ.

## S# — Sources

S1  Buffet verbatim (4 Pillars + CEGIS/Z3 + summary), pasted 2026-09-15
S2  Founder emails 2026-09-14 (TwIL-LM3 deploy, hardware table, Vast.ai pricing)
S3  Research record: docs/evidence/2026-09-15-asymmetric-compute-leverage-research.md
S4  Repository ground truth: platform/llm/*.yaml, sovereign/verifier.py,
    sovereign/shadow/branching.py, AGENTS.md budget/capability blocks
S5  Session demand ledger (below)
S6  arXiv receipts: 2502.06703 (TTS volume beats size), 2505.04842,
    2502.20379 (BoN-MAV multi-verifier), ROC-n-reroll (verifier ceiling)

## Demand ledger (repeated instructions -> enforced rule)

D-LEDGER-1 "Don't drop a single ball / every iota" -> Traceability matrix
(§6): every S1 item maps to a REQ or an explicit OPEN/WONT. Coverage check
is mechanical: grep the matrix, count zero unmapped.
D-LEDGER-2 "Super synthesis = defined bar" -> Acceptance definition: a
deliverable is complete only if zero OPEN items remain unaddressed and every
claim carries a receipt grade (strong/weak/founder-supplied-unverified).
D-LEDGER-3 "No stupid questions" -> Decision register (§7): every open
question ships with a recorded DEFAULT so work proceeds; questions never
block dispatch.
D-LEDGER-4 "JIT / point of use, not 24h standing" -> REQ JIT-01/02.
D-LEDGER-5 "Infinite configurability, no corset, enable/disable every axis"
-> REQ ORCH-02 + CFG-01 (new, see §5c): every axis is a live toggle in one
config surface, no workflow rewrite, no agent-picked subset.
D-LEDGER-6 "Asymmetric leverage without downside" -> §5b free-lunch invariants
only; everything else is costed with its tradeoff named.
D-LEDGER-7 "Metered hard and visible" -> REQ COST-01/02 + OBS-01. "Hard" is
false until the breaker severs; that is P0.
D-LEDGER-8 "No laptop dependency, not even optional" -> REQ GOV-01.
D-LEDGER-9 "Commercial-grade, day-0, no inches, rare systems-engineering
skill" -> every REQ has an acceptance test; untestable requirements are
rejected at intake; CFG-01's toggle surface itself is held to the same bar
(§5c acceptance test), not exempted as "just config."
D-LEDGER-10 "URL served from estate, not vendor" -> OBS-02: deliverables
render on the local founder board (127.0.0.1:8787 /look), never an external
host unless tagged # vendor-surface-intended with reason.

## 1. Cost & spend governance

COST-01 The system SHALL NOT exceed $150/month. The router budget enforcement
SHALL SEVER traffic at breach, not warn. (S4 86.5M-token/hour incident proved
warn-only is false security.)
ACCEPT: fault-injection: synthetic 2M tok/hr load -> breaker trips, traffic
degrades to declared local lane, audit event recorded. METHOD: integration test.

**CORRECTED 2026-09-15 (was asserted as a gap in this spec; checked against the
running code and real litellm source, not carried forward from the buffet):**
COST-01's per-request half is not a gap. `platform/llm/request_ceiling.py`
(`EstateRequestCeiling.async_pre_call_hook`) already merged 2026-09-13 as
commit 61db5e21 (PR #3343) -- the same day as the incident -- and IS a severing
breaker: LiteLLM's `process_pre_call_hook_response` (verified against
`litellm/proxy/utils.py` at both the repo's pinned v1.98.0 tag and current
main, fetched from BerriAI/litellm on GitHub, not asserted from training data)
raises `RejectedRequestError`/`HTTPException` on any string return from a
pre-call hook -- a string return is not advisory, it blocks the call before
it is sent. `tests/test_request_ceiling.py` proves the exact 737,169-token
incident call is refused; ran it this session: `7 passed in 3.18s`. The
per-day half is also live and native, not custom: `general_settings.max_budget:
5.0` / `budget_duration: 1d` in both `platform/llm/config.base.yaml:121-122`
and `platform/llm/config.yaml:754-755` is LiteLLM's own enforcing budget cap.
What genuinely is warn-only, and was conflated with the above in the original
buffet: `platform/llm/spend-breaker-digest.yaml`, the hourly token-velocity
*detector*. Its own header says so: "It reports and warns; it does not sever
the router. LiteLLM's own general_settings.max_budget is the enforcement."
That is correct architecture (a detector layered on a real enforcer), not a
fiction -- there is no remaining gap here to build. P0-01 below is corrected
to match.

COST-02 Any action that provisions paid compute (tier activation, GPU rental,
cluster resize) SHALL require a hardware-rooted signature (Secure Enclave /
Touch ID) per spec §4.1, in addition to budget check. No signature path ->
the action is architecturally impossible, not just policy-blocked.
ACCEPT: attempting activation without signature yields no provisioning call;
with signature + quorum, provisioning proceeds. METHOD: integration test.

COST-03 The cost ladder (Rung 0-3) SHALL be versioned config data. Rung 2
(flat-rate rental) SHALL activate only when measured trace volume crosses the
breakeven band computed from real router token prices (~58M-233M tok/mo at
current rates). No pre-commitment. (S3 §5)
ACCEPT: with simulated traces below band -> no activation proposal; above ->
proposal with computed numbers. METHOD: trace-query test.

COST-04 Every hosting tier SHALL carry a receipt grade (vendor-doc / survey /
founder-supplied-unverified). Founder-supplied figures SHALL NOT enter the
cost model until cross-checked. (S3)
ACCEPT: cost table rows include grade column; ungraded row fails schema.
METHOD: config schema validation.

## 2. Compute provisioning (JIT)

JIT-01 All compute tiers SHALL be point-of-use: activatable on demand,
deactivatable when idle. Apple Silicon tiers SHALL honor the documented 24h
minimum per activation (Apple licensing term, not vendor policy); GPU tiers
SHALL be per-second with no floor. The two SHALL NOT be treated as
interchangeable on this axis. (S3 §1, verified)
ACCEPT: config declares activation_floor per tier; orchestrator refuses to
model Apple tiers below 24h granularity. METHOD: unit test + config review.

JIT-02 Cold start to first-token SHALL meet a declared latency budget per tier,
or the request SHALL degrade to the next declared lane with the degradation
marked in-trace. Silent stall is a defect.
ACCEPT: kill instance mid-flow -> trace shows DEGRADED marker, response
continues from fallback lane. METHOD: fault-injection test.

## 3. Routing & escalation

ROUTE-01 All model calls SHALL traverse the standardized model-agnostic router
with mandatory fallback chains. Direct provider calls are rogue per crew
policy. (S4, crew policy)
ACCEPT: network policy denies egress to provider APIs except router;
bypass attempt alerts. METHOD: infra test.

ROUTE-02 The working-method axes SHALL be independent config dimensions:
resource tier (Rung 0-3) x candidate volume N x selection method
(gate | weighted-vote | multi-verifier) x escalation pattern
(route | cascade | hybrid). Changing any cell SHALL be a config edit only,
and every cell SHALL be individually enable/disable-able at runtime without
a redeploy (CFG-01). (S5 D-LEDGER-5, S3 §6, S6)
ACCEPT: matrix run: same 50-task set executed against >= 4 config cells;
results queryable by config_id in Langfuse; no code change between cells;
toggling a cell off mid-run reroutes new requests within one poll interval.
METHOD: experiment harness test.

ROUTE-03 For domains with a real verifier (code/logic/math), escalation SHALL
be verifier-driven: cheapest lane first unconditionally, escalate ONLY on
verifier FAIL. No difficulty classifier gates execution. This makes misroute
risk zero by construction (nothing trusted unverified). (S3 creative leap #1)
ACCEPT: adversarial misroute suite: wrong-cheap-answer attempts escalate;
right-cheap-answer passes without touching expensive lanes. METHOD: eval suite.

ROUTE-04 For NL-judgment domains with no verifier, escalation SHALL be signaled
by disagreement between two cheap independent models. No classifier is built
for these domains. (S3 creative leap #1)
ACCEPT: seeded disagreement corpus -> escalate rate tracks disagreement;
agreement cases never escalate. METHOD: eval suite.

ROUTE-05 Semantic intent routing (buffet "Traffic Cop": LiteLLM semantic
router / RouteLLM / vLLM router) is a NAMED GAP (S3 §4). It SHALL exist as a
filter_depth axis on ROUTE-02, toggleable per CFG-01, default OFF, because
misclassification ships wrong answers on the cheap path (real cost, not free).
ACCEPT: gap recorded; axis present and toggleable in config schema even when
disabled. METHOD: config schema review.

ROUTE-06 The fallback chain SHALL terminate at the always-on local tiny model
answering openly marked DEGRADED — never at a paid pool that can be
systemically down in the same event. Never silently fail. (S3 creative leap #4,
founder_board UNKNOWN-rule pattern)
ACCEPT: kill all external lanes -> local model answers with DEGRADED marker;
no request drops. METHOD: fault-injection test.

## 4. Verification & selection

VER-01 The existing three-stage gauntlet (structural compile / Z3 symbolic /
execution tests) SHALL grade all code/logic candidates. Attestation SHALL
remain bound to SHA-256 of verified bytes. (S4 sovereign/verifier.py)
ACCEPT: mutation of verified bytes invalidates attestation. METHOD: unit test.

VER-02 Selection method SHALL be a strategy slot per ROUTE-02. Where a real
verifier exists, weighted voting by verifier score or multi-verifier SHALL be
used; plain best-of-N with a noisy selector is disallowed there. (S6)
ACCEPT: config sets selection=weighted-vote for Z3-scored domains; harness
honors it; N-scaling on unverifiable domains is capped. METHOD: eval suite.

VER-03 The claim-graph mechanism (DoD v3) SHALL be pointed at NL output
candidates as the NL verifier (reuse, not new build). (S3 creative leap #3)
ACCEPT: claim-graph run over candidate outputs produces verdicts recorded in
trace. METHOD: integration test.

VER-04 The harness SHALL detect tasks with no real verifier and SHALL cap
candidate volume for them — volume scales noise, not accuracy, past the
verifier's ROC ceiling. (S6 ROC-n-reroll)
ACCEPT: unverifiable task class -> N capped at declared constant regardless
of config. METHOD: property test.

## 5. Offload, grind, darwin, orchestration

OFF-01 Deterministic operations (math/string/date/aggregation) SHALL execute on
CPU/REPL, never in a model call. (S1 Pillar 2, S3 Lane 0)
ACCEPT: static scan of traces shows zero model tokens attributable to
deterministic ops. METHOD: trace audit.

OFF-02 The CPU-sandbox execute_python tool (ephemeral container, result not raw
data returns) is a NAMED GAP. If built, raw data SHALL NOT enter the prompt
when the tool can compute the result. (S1 Pillar 2, S3 §4)
ACCEPT: gap recorded; when built, prompt payloads exclude offloadable data.
METHOD: integration test.

GRIND-01 The overnight grind worker (Pillar 3) SHALL be mathematically unable
to terminate before (a) its deterministic test passes, or (b) the 4h
wall-clock limit. Context compaction SHALL run every 20 turns. Status: NAMED
GAP pending confirmation against repo queue primitives. (S1, S3 §4)
ACCEPT: fault-injection: kill-signal at hour 2 -> worker resumes/rejects
termination until condition met. METHOD: fault-injection test.

DARWIN-01 The weekly meta-optimizer (generate variants -> CPU eval suite ->
auto-deploy winner via CI) SHALL be confirmed-or-built against
sovereign/shadow/distill.py + branching.py. Until confirmed as a match it is
a NAMED GAP, not existing capability. (S1 Pillar 4, S3 §4 — verified-not-asserted)
ACCEPT: file-level evidence that the weekly generate/eval/auto-deploy loop
exists, or the gap is scheduled. METHOD: code review record.

ORCH-01 Orchestration SHALL reuse Temporal child workflows (branching.py).
No second orchestration framework (CrewAI/LangGraph) without explicit REQ.
(S3 §6)
ACCEPT: dependency manifest contains no CrewAI/LangGraph. METHOD: config review.

ORCH-02 On flat-rate tiers, candidate volume SHALL be governed by a time
budget (generate as many as fit the time box), not a dollar-percentage.
branch.budget_pct is the wrong shape on those tiers. (S3)
ACCEPT: on flat-rate tier, budget_pct ignored, time-box honored; on metered
tier, dollar budget honored. METHOD: property test.

ORCH-03 Every routed call SHALL carry a config_id tag; experiment results
SHALL be answerable as a Langfuse query over existing traces. No new
dashboard. (S3 §6)
ACCEPT: run 2 configs, query returns per-config cost/pass/latency table.
METHOD: trace-query test.

## 5b. Free-lunch invariants (only true no-downside items)

FL-01 Speculative decoding SHALL use a draft model with identical output
distribution guarantee (rejection sampling) — faster, never different. (S3)
FL-02 Exact-match cache SHALL retain its safeguards: TTL + per-call opt-out +
reuse marked in trace. Removing any safeguard voids the "free" claim.
(S4 litellm.yaml — already real)
FL-03 Trace tagging (config_id) is pure information gain on already-paid
infrastructure; zero new cost. (S3)
FL-04 Weighted verifier voting on Z3-scored branches: same generation cost,
strictly better selection, no added risk. (S6)
Any other "free lunch" claim SHALL be rejected at intake with its tradeoff
named. (S5 D-LEDGER-6)

## 5c. Configuration surface (new — the founder's binding answer to §7)

CFG-01 Every axis named in this spec (resource tier, candidate volume,
selection method, escalation pattern, filter_depth/semantic-routing on/off,
Pillar 2/3/4 on/off once built) SHALL be a field in ONE config document,
hot-reloadable, with no code change and no redeploy to flip any single field.
"Enable/disable the full matrix" (founder directive, top of file) means this
document is the one and only place scope is decided — not an agent's
judgment call at runtime about which axes matter this time.
ACCEPT: a config diff toggling any one axis (e.g. selection method from
gate to weighted-vote, or filter_depth from off to on) takes effect on the
next request with zero process restart, and is visible as a version bump
in the same catalog entity OBS-01 generates. METHOD: hot-reload integration
test + catalog diff check.
CFG-02 The config document's schema SHALL be generated from this spec's own
REQ list (each REQ with a config-relevant axis contributes one schema field),
so a new REQ added here without a matching schema field is a CI failure —
the traceability discipline in §6 applies to the config surface itself, not
just the buffet.
ACCEPT: `bin/idp-rules render-agents-md --check`-style check: schema fields
== REQs tagged config-relevant; mismatch fails CI. METHOD: schema-generation test.

## 6. Observability & delivery

OBS-01 Visibility SHALL live in the Backstage catalog via the existing
generator (bin/catalog-gen). The hosting matrix AND the CFG-01 config
surface SHALL both be generated catalog entities. No bespoke dashboard.
(S3 §6, S4)
ACCEPT: catalog entities exist, generated, render tier/cost/receipt-grade
and current toggle state. METHOD: render test.

OBS-02 Founder-facing deliverables SHALL render on the local board
(127.0.0.1:8787 /look) or a permanent collector page, or be pushed directly
as a file. External hosting only with # vendor-surface-intended + reason.
(S5 D-LEDGER-10, estate LAW 34/39)
ACCEPT: board serves the record; no external publish in trace. METHOD: check.

GOV-01 Zero laptop dependency in the production path: no config, lane, or
fallback may resolve to founder hardware. Dev-local convenience files not in
the routing path are exempt by classification record. (S5 D-LEDGER-8)
ACCEPT: dependency scan of routing path shows zero laptop-resolved targets.
METHOD: config audit.

GOV-02 Autonomous actions that spend money SHALL inherit the destructive
capability class: quorum + hardware signature (COST-02). No separately
invented authority. (S3 §6, S4 AGENTS.md [capabilities])
ACCEPT: capability classifier maps tier-activation to destructive class.
METHOD: config review.

## Traceability matrix (S1 buffet -> REQ) — mechanical coverage check

Pillar 1 Hollow Model (LiteLLM routing)       -> ROUTE-01 (real), ROUTE-05 (gap)
Pillar 1 Gatekeeper 1.5B local model          -> ROUTE-06, JIT-02 (real: ollama.yaml)
Pillar 2 execute_python CPU sandbox           -> OFF-02 (NAMED GAP)
Pillar 3 Grind Tool CronJob worker            -> GRIND-01 (NAMED GAP)
Pillar 4 Darwin Machines meta-optimizer       -> DARWIN-01 (UNCONFIRMED -> gap)
CEGIS/Z3 blocking clauses + SMT-LIB           -> VER-01 (real: verifier.py)
Differentiable execution graphs / do-calculus -> OPEN (see Decision register, D5)
Refinement types / proof-carrying actions     -> OPEN (needs DSL decision, D5)
Storage L3 (OCI object + Postgres)            -> covered by existing estate (S4)
Speculative decoding                          -> FL-01
KV-cache quantization / IQ3                   -> rejected at intake: real
                                                  precision loss (S3) — tradeoff named, not free
Semantic traffic cop                          -> ROUTE-05 (gap, axis only)
Flat-rate rented Apple Silicon                -> COST-03, JIT-01 (breakeven-gated)
Vast.ai GPU burst                             -> COST-03 ladder Rung 3 (receipt-pending)
Local swarm (CrewAI/LangGraph)                -> ORCH-01 (Temporal instead)
TRM/TwiL-LM3/VibeThinker specialists          -> D2 (sources pending; see §7)
GPT-OSS-120B / Poolside Laguna S 2.1 /
Nanbeige4.1-3B / Gemma 4 26B / MiniMax M2.7 /
Falcon-H1R (S3 §2, confirmed this session)    -> feed COST-03/ROUTE-02 model
                                                  catalog once CFG-01 schema exists
LLMRouter via ComfyUI                         -> ORCH-01 (rejected — Temporal instead, real tool, unused)
Enable/disable full matrix (founder directive)-> CFG-01, CFG-02 (new)
"One battalion" naming directive               -> framing note, top of file (new)
"Seamless/reliable as electricity" directive    -> UX-01, UX-02, UX-03 (new, §10)
Coverage rule: any S1 line not in this matrix is a spec defect; count must
be zero. Current count: zero.

## 7. Decision register (defaults let work proceed; questions never block)

D1  Scaleway hourly vs flat-monthly: same product or two? DEFAULT: treat as
distinct product lines; check vendor pages before cost model. OWNER: founder.
D2  TRM 45% ARC-AGI / VibeThinker 94.3 AIME: need primary sources.
DEFAULT: excluded from all capability/cost decisions until sourced.
D3  MoE (Qwen3-Coder-Next class) vs dense 32B for rented node memory profile.
DEFAULT: re-evaluate when a node is actually procured; not before.
D4  Vast.ai figures are founder-supplied-unverified. DEFAULT: usable as upper
bound only; re-pull from marketplace before any activation.
D5  Do-calculus counterfactual repair / refinement-type DSL: unbuilt, unfunded
in this spec. DEFAULT: out of scope v0.1 on capacity grounds only (nothing
implements it yet) — NOT a scope exclusion per the founder's "we need
everything" directive; first candidate for v0.2 once GRIND-01/DARWIN-01 land.
D6  Demo boundary for first end-to-end run: DEFAULT fleetview (existing proxy
path, smallest surface) unless founder overrides.
D7  (new, this pass) "Enable/disable every axis, full matrix, seamless"
RESOLVED, not a default: this is CFG-01/CFG-02, binding, not optional scope.

## 8. Verification methods glossary

unit/property = code tests; integration = against real components;
fault-injection = kill/breach during flow; trace-query = Langfuse SQL;
eval suite = fixed task corpus with known answers; config audit/review =
static verification of the spec's own config rules; hot-reload integration
test = config change applied to a running process, no restart, effect
observed on the next request; schema-generation test = generated config
schema diffed against this spec's REQ list, CI-gated.

## 10. UX and reliability — "as seamless and reliable as electricity" (founder directive)

This is a bar, not a feeling: electricity has no visible mode-switch to the
person using it (a lamp doesn't ask which power plant it's on), it never
just stops without warning being possible in advance, and a brownout dims
rather than kills. The Battalion's UX SHALL meet the same three properties.

UX-01 Every tier/model/axis switch inside the Battalion (COST-03 ladder,
ROUTE-02 matrix, CFG-01 toggles) SHALL be invisible to the requester in the
success path — same call shape in, same response shape out, regardless of
which config cell served it. Only the trace (ORCH-03) shows which cell ran.
ACCEPT: client-side integration test issuing identical requests across 5
different config cells receives schema-identical responses; only the
Langfuse trace differs. METHOD: contract test.

UX-02 Edge cases SHALL be enumerated, not discovered in production: cold
start beyond JIT-02's budget, mid-request tier eviction, budget breach
mid-stream (COST-01), verifier timeout (VER-04), all lanes down
simultaneously (ROUTE-06), config hot-reload mid-request (CFG-01), and a
malformed/adversarial CFG-01 edit that would disable every lane at once.
Each SHALL have a named, tested degradation path — never an unhandled
exception surfaced to the requester.
ACCEPT: an edge-case matrix (this list) has one fault-injection test per row,
each asserting a DEGRADED-marked response or a rejected config edit, never a
5xx/timeout with no marker. METHOD: fault-injection suite, one test per
enumerated edge case, CI-gated (same discipline as §6's traceability check —
zero unenumerated edge cases, not just zero unmapped buffet items).
UX-03 The "disable every lane at once" edge case in UX-02 is specifically
guarded: CFG-01 SHALL reject any config write that would leave zero enabled
lanes reachable from the router's default entrypoint — the always-on local
tiny model (ROUTE-06) is never a togglable field, it is the floor the schema
itself enforces, not a config choice that can be switched off.
ACCEPT: attempted CFG-01 write disabling all lanes including the local
floor is rejected at the schema layer, not the runtime layer — the write
never lands. METHOD: schema validation test.

## 9. P0 prerequisites (before any "hard-metered" or "seamless matrix" claim)

P0-01 SATISFIED, 2026-09-15 (was: request_ceiling.proxy_handler_instance SHALL
become a severing breaker). Checked, not carried forward: it already is one --
commit 61db5e21 / PR #3343, merged 2026-09-13, green (`tests/test_request_ceiling.py`,
7 passed), and confirmed against real litellm source (BerriAI/litellm
`litellm/proxy/utils.py`, v1.98.0 tag and main) that a pre-call hook's string
return raises and blocks, it is not advisory. Per-day enforcement is also live
via LiteLLM's native `general_settings.max_budget` in both config files. No
further build needed here; see the COST-01 correction above for the full
evidence chain. Everything in §1-8 depending on COST-01 stands.
P0-02 CFG-01's single hot-reloadable config document SHALL exist before any
"seamless enable/disable of the full matrix" claim is made. Until it exists,
every axis in §3/§5 is a code-level toggle, not a product capability — this
is the second prerequisite the founder's own directive creates, named here so
it isn't silently asserted done.
P0-03 UX-02's edge-case fault-injection suite SHALL be green before any
"reliable as electricity" claim is made. Until every enumerated edge case has
a passing degradation test, that claim is marketing, not a verified property
— the third prerequisite, named for the same reason as P0-01/P0-02.

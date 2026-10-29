# Estate — Master Vision, Epic Register and Recovered Specifications

**Compiled:** 2026-10-29 08:16 UTC
**Classification:** Recovery compilation, NOT a certified exhaustive historical record or a production status report.
**Target:** `chidionyema/idp`

## 0. How to use this document

This is a preservation-first compilation. The complete text of each accessible source specification is reproduced below, without silently rewriting its requirements. The epic register is a synthesis of prior discussions and is NOT a substitute for original source documents. Missing historical specifications are explicitly marked for recovery.

**Evidence levels:** `SOURCE INCLUDED` means full original source reproduced here; `REPO REFERENCED` means named in a recovered source or earlier repository inspection but not reproduced here; `DISCUSSION SYNTHESIS` means recovered from discussion rather than an original source; `NOT VERIFIED` means live operational state has not been established.

## 1. North star

Estate is a governed, autonomous, evidence-led engineering and commercial enterprise that can interpret founder intent, discover its capabilities, plan and coordinate work, investigate unknowns, execute within authority, independently verify outcomes, operate and repair its infrastructure, learn from measured consequences, and reduce founder intervention.

**Traceability chain:** Founder intent → objective → epic → requirement → source specification → capability → implementation → deployment → operational proof → outcome → learning.

## 2. Master epic register — preliminary domain taxonomy

| ID | Domain | Source coverage in this compilation |
|---|---|---|
| E-01 | Founder command, 360/720 enterprise picture and intent | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-02 | Governance, sovereignty, claims and decision authority | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-03 | Portfolio planning, master epics and congruency | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-04 | Autonomous workforce, agent factory and departments | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-05 | Autonomous engineering, execution and code intelligence | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-06 | Greenlane, CI/CD and production delivery | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-07 | Infrastructure, capacity, disk and recovery | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-08 | Observability, incident response and self-healing | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-09 | Independent verification, evidence and certification | SOURCE INCLUDED (certification only) |
| E-10 | Context, retrieval, knowledge graph and Oracle | SOURCE INCLUDED |
| E-11 | Research Engine and autonomous Science | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-12 | Reasoning intelligence and adaptive method selection | SOURCE INCLUDED |
| E-13 | Model routing, free lanes and inference economics | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-14 | Finance, resource allocation and budgeting | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-15 | Special Forces, products and commercialisation | SOURCE INCLUDED |
| E-16 | Marketing, growth and customer discovery | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-17 | Media, film, virtual worlds and avatars | SOURCE INCLUDED |
| E-18 | Identity, Otto, Concierge and interaction | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-19 | Security, secrets, trust and resilience | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |
| E-20 | Learning, reflexivity and organisational self-improvement | DISCUSSION SYNTHESIS / SOURCE RECOVERY REQUIRED |

This register is intentionally a domain-level index; it does not claim to enumerate every historical issue or sub-epic. Reconciliation must extract each original epic and its requirement IDs, then deduplicate by canonical identity without deleting historical versions.

## 3. Enterprise-wide non-negotiables

1. No assertion of operational status without observed real-caller production evidence.
2. No duplication of established engines, context stores, schedulers, execution paths or evidence systems without measured justification.
3. Every action has an identified decider, authority and provenance.
4. Every acceptance gate must include a falsifier and demonstrate rejection of an invalid case.
5. Work follows issue claim and Greenlane governance; do not hand-push main or bypass the established executor.
6. Retain original source text and supersession history; conflicting requirements are recorded as conflicts, not silently resolved.
7. Live source-of-truth outranks stale representations for claims about current runtime state; historical decisions remain historically authoritative.
8. Founder-facing 720-degree view must show coverage gaps and uncertainty, not only successes.

## 4. Known cross-cutting gaps and risks

| Gap | Evidence or origin | Required reconciliation |
|---|---|
| Fragmented epic/spec inventory | Repeated founder requests for comprehensive 360/720 view | Enumerate repository specs, epics, ADRs, issues, and available historical documents |
| Claimed completion vs actual proof | Uploaded 27–29 October incident transcript; AGENTS.md proof rule | Separate work claims from verification and operational evidence; enforce only appropriate stage-specific proofs |
| Disk/worktree amplification | Uploaded incident transcript describes 35 worktrees × 176 MB tracked duplication; historical observation, not a current measurement | Source-grounded RCA; ensure safe provisioning without touching live agents |
| Governance BLIND | Transcript repeatedly shows grader timeouts | Observe and report blind enforcement; fail safe without unbounded work or invented verdicts |
| Agent action worsens failure | Incident transcript describes repeated manual intervention and failure to land systemic fix | Introduce bounded intervention, stop conditions, ownership and independent outcome checks |
| Unclosed research loop | Master epic review described research → ticket → science → prototype as partial | Verify event-to-dispatch-to-production path |
| Source and live-state contradiction | Context substrate RFC | Typed authority/freshness rules and explicit conflicts |
| Unverified operation | Source specs explicitly labelled proposed/not certified | Verify through real production caller, traces and logs |

## 5. Source inventory and completeness

| Source | Status | Bytes |
|---|---|---:|
| `IDP_Estate_Context_Substrate_RFC_v0_1.md` | FULL TEXT PRESERVED | 23,856 |
| `IDP_Production_Certification_Implementation_Plan_v1.md` | FULL TEXT PRESERVED | 15,214 |
| `IDP_Autonomous_Media_Department_Charter_v1.md` | FULL TEXT PRESERVED | 13,520 |
| `Estate_Special_Forces_Operationalisation_Spec_v1.md` | FULL TEXT PRESERVED | 23,457 |
| `estate_reasoning_repertoire/OPERATIONAL_SPEC.md` | FULL TEXT PRESERVED | 7,323 |
| `Pasted markdown.md` | INCIDENT EXCERPT, not an epic spec; evidence summary only | 80,521 |

### Repository sources requiring separate recovery

- `AGENTS.md` — programme tenets, seven cognitive gates, claims, Greenlane and operational proof.
- `docs/epics/2026-10-25-estate-master-epic.md` — programme of record, requirement register, gaps and phases.
- `docs/decisions/0037-the-film-is-a-deterministic-twin-of-the-event-spine.md`.
- `docs/specs/2026-10-23-estate-as-movie-director-engine.md`.
- `docs/research/2026-10-25-virtual-world-vs-realtime-film.md`.
- Additional GitHub issues, ADRs, specs, research documents, earlier conversation artifacts and superseded versions — NOT exhaustively enumerated here.

## 6. Recovery protocol for a certified complete register

1. Inventory all repo `docs/epics`, `docs/specs`, `docs/decisions`, `docs/research`, runbooks and archived branches; record path, SHA, date, authority and status.
2. Export all GitHub issues, discussions, relevant PR descriptions and linked acceptance criteria; preserve immutable URLs and timestamps.
3. Recover accessible prior specifications and founder decisions from conversations and files.
4. Extract requirements as atomic, source-linked records; assign canonical IDs and preserve original wording.
5. Detect duplicates, supersessions, contradictions, orphaned implementations, missing evidence and unowned capabilities.
6. Join requirement → implementation → tests → deployment → live operational evidence using verified references.
7. Produce versioned enterprise graph, change log and gap report; publish only through governed Estate process.
8. Require an explicit coverage manifest and list of inaccessible sources before describing the register as exhaustive.

---

# PART II — RECOVERED ORIGINAL SPECIFICATIONS (VERBATIM)

The following sections preserve the complete text of accessible source documents. They are not merged into a new synthetic specification; disagreements remain visible.


---

## SOURCE 1: Context and Retrieval

**Original file:** `IDP_Estate_Context_Substrate_RFC_v0_1.md`

**Preservation:** complete source text follows.

# RFC: IDP Estate-Wide Context and Knowledge Substrate

**Status:** Proposed / source-grounded engineering specification (2026-10-28). **Not** an implementation-complete or production-certified claim.

**Repository:** `chidionyema/idp`, `main`, inspected via connected GitHub source. **Scope:** all estate consumers, not merely epistemic evidence or Oracle.

## 0. Executive decision

**Extend, do not replace, the estate's existing context stack.** The repository already contains a substantial context compiler, policy broker, Gortex indexing pipeline, memory service, estate graph, catalog, and event capture. Building a new generic RAG stack would duplicate implemented functionality and violate the estate's one-engine design. The missing product is a *federated, task-specific context service* spanning code, operational state, structured topology, decisions, history, and authenticated evidence, using existing systems as authorities. A retrieval hit must never silently become an assertion of live truth.

**Architecture rule:** One policy entry point and common context envelope; multiple *source-of-truth adapters*, not a second ranker or universal vector store. Existing Gortex owns code ranking. Unified memory owns memory retrieval. Kubernetes/Git/CI own their live and historical state. Context compilation merges typed evidence under explicit authority and freshness rules.

## 1. Source-verified baseline

| Capability | Source | Verified from source | Not established |
|---|---|---|---|
| Policy broker | `platform/estate/context/broker.py` (764 lines) | freshness decisions; read-only tool allowlist; path and token budget decisions; secret scrubbing; provenance; engine client | live gateway bypass resistance, authorization correctness in deployed environment |
| MCP broker | `platform/estate/context/server.py` (767) | `estate_context` and `estate_context_status`; `/mcp`; claim lookup; index manifest; metrics; source excerpt handling | live service availability, agent coverage |
| Compiler | `platform/estate/context/plan.py` (609), `bin/estate-context-compile` (725) | deterministic ContextPlan, engine order preservation, token budget, source digests, catalog/affected-graph integration | representative real-world retrieval quality |
| Local fallback | `platform/estate/context/local_engine.py` (195) | Gortex CLI adapter and freshness reporting | whether installed on all agent hosts |
| CI index build | `.github/workflows/context-index.yml` (220) | pins Gortex v0.64.11; checks index commit and live smart_context answer; publishes signed OCI artifact | latest workflow success; whether all intended repositories indexed |
| Broker deployment | `platform/mcp/estate-context-broker.yaml` (239) | private loopback Gortex sidecar; broker container; OCI index pull; PVC | actual pod health; authenticated gateway routing |
| Broker verification | `bin/estate-context-gate` (901); `tests/test_estate_context_broker.py` (316); `tests/test_estate_context_compile.py` (645) | source includes fail-case tests, policy gates, catalog checks | tests not executed in this review |
| Unified memory | `platform/unified-memory-server/main.py` (1337), `ranking.py` (95) | memory write/read/history/search/recall/brief, embedding status/backfill, harness prefetch/consolidate | live embedding backend health; retrieval quality |
| Memory MCP adapter | `mcp/plugins/estate_memory.py` | structured memory ingest; R1/R2/R3 probe and trust tier | end-to-end operational success |
| Estate topology | `bin/idp-affected-graph`, `bin/catalog-projection`, Backstage entity providers | code and catalog paths exist and compiler consumes their results | completeness and edge correctness |
| Conversational graph | `platform/llm/graph_capture.py`, `bin/estate-graph-drain` | router capture and graph-drain pipeline exists | full coverage, durability and quality |
| Evidence | `bin/estate-claim-check`, Aevum and local gates | claim re-execution and evidence recording | semantic entailment, unified authority |

**Source links:**
- https://github.com/chidionyema/idp/blob/main/platform/estate/context/broker.py
- https://github.com/chidionyema/idp/blob/main/platform/estate/context/server.py
- https://github.com/chidionyema/idp/blob/main/platform/estate/context/plan.py
- https://github.com/chidionyema/idp/blob/main/.github/workflows/context-index.yml
- https://github.com/chidionyema/idp/blob/main/platform/unified-memory-server/main.py
- https://github.com/chidionyema/idp/blob/main/platform/mcp/estate-context-broker.yaml

## 2. System boundaries and invariants

1. **No new code indexer or ranker.** Use the existing Gortex versioned code index and its smart_context, symbol, and graph tools. Other source-specific retrieval engines may rank within their own domains; cross-domain merging uses deterministic policies, not a duplicate semantic ranker for code.
2. **No shadow memory store.** Unified memory remains the source for remembered decisions, preferences, incidents and measurements. Index projections may be rebuilt from authoritative data but cannot become write authorities.
3. **No operational assertions from cached documents.** Questions with `requires_live=true` must query live authoritative APIs or return `UNKNOWN/UNAVAILABLE`; historical context is supplemental.
4. **One broker for client-facing context.** Add capabilities to existing MCP broker, preserving existing `estate_context` contract. Never expose private engine credentials to consumers.
5. **Evidence is typed.** Every result identifies source type, immutable revision or observation time, method, and confidence *category*; no uncalibrated numeric confidence scores.
6. **No silent fallback.** Every unavailable source appears as a coverage gap. A partial result cannot be labelled complete.
7. **Read-only context retrieval.** Retrieval never mutates cluster, repository, tickets, or memory. Any remedial action passes the existing execution and authorization plane.
8. **Isolation by principal.** All adapters enforce caller identity, repository scope, namespace and data classification. Retrieval cache keys include the authorization scope and relevant revision.
9. **Budget before generation.** Token/latency/fanout limits are enforced before returning material; refusal reports the measured or bounded reason.
10. **Traceable decisions.** Each answer includes query ID, policy decisions, sources used, omissions, freshness status and reproducible reference IDs.

## 3. Query contract

Expose a new versioned tool `estate_context_resolve_v1` through the existing MCP broker. Keep `estate_context` and `estate_context_status` backward compatible. The following is a **proposed** API, not an existing implementation:

```json
{
  "query": "What would break if the unified-memory service were restarted?",
  "intent": "impact_analysis",
  "scope": {"repositories": ["chidionyema/idp"], "namespaces": ["estate"]},
  "temporal": {"mode": "live", "as_of": null, "max_age_seconds": 60},
  "evidence": {"minimum": "source_attributed", "require_independent_witness": false},
  "limits": {"token_budget": 4000, "deadline_ms": 5000, "max_sources": 24},
  "claim": {"issue": 0, "agent": ""}
}
```

**Request validation:** query 1–4096 Unicode characters; intent from enumerated list (`code_navigation`, `change_impact`, `runtime_diagnosis`, `incident_analysis`, `decision_recall`, `policy_lookup`, `estate_question`); temporal mode `commit|as_of|live`; `as_of` required for historical time travel; commit SHA required for commit mode unless broker resolves a pinned commit; deadline 250–30000ms; token budget 256–32000; max_sources 1–100. Reject unknown scopes and invalid combinations. Do not make `claim.issue=0` a privileged bypass: read-only access policy must explicitly define whether claims are required, based on existing broker governance.

Response shape:

```json
{
  "schema_version": "1.0",
  "query_id": "opaque-request-id",
  "status": "PARTIAL",
  "answerability": "SUPPORTED_WITH_GAPS",
  "as_of": "2026-10-28T12:00:00Z",
  "context_plan": {"items": [], "used_tokens": 0, "plan_hash": "sha256:..."},
  "sources": [{
    "id": "src-1", "type": "git_source", "authority": "github",
    "locator": "repo:path#L10-L30", "revision": "full-git-sha",
    "observed_at": null, "retrieved_at": "2026-10-28T12:00:00Z",
    "digest": "sha256:...", "verification": "SOURCE_AUTHENTICATED",
    "claims_supported": ["claim-1"]
  }],
  "claims": [{"id":"claim-1","text":"...","support":["src-1"],"status":"SUPPORTED_SOURCE"}],
  "gaps": [{"source":"kubernetes","reason":"TIMEOUT","impact":"live state unknown"}],
  "policy": {"scope":"allowed","freshness":"partial","redactions":0},
  "timing_ms": {"total":0},
  "cache": {"hit":false,"key":"..."}
}
```

**Statuses:** `COMPLETE`, `PARTIAL`, `REFUSED`, `UNAVAILABLE`, `INVALID_REQUEST`. **Claim statuses:** `SUPPORTED_SOURCE`, `LIVE_OBSERVED`, `REEXECUTED`, `CONTRADICTED`, `UNVERIFIED`, `STALE`. `SUPPORTED_SOURCE` means a specific source passage was retrieved and attributed; it does *not* imply entailment or real-world truth. Use `REEXECUTED` only with a proposition-bound checker and matched result.

## 4. Federated retrieval adapters

Each adapter implements `discover(request) -> Candidate[]`, `hydrate(candidate, budget) -> Evidence[]`, `health() -> Status`. Adapter discovery is bounded, parallel where safe, and always returns structured errors. No adapter may create an LLM call merely to enumerate candidates.

| Adapter | Existing authority | Initial query modes | Freshness rule |
|---|---|---|---|
| `code` | Gortex through existing broker engine client | symbols, implementations, callers, tests, code impact | indexed commit must equal requested commit; working-copy caveat preserved |
| `catalog` | Backstage/catalog projection and `idp-affected-graph` | service owners, topology, dependencies | projection revision/time reported; unobserved edges labelled declared |
| `memory` | unified-memory HTTP API | decisions, incidents, previous investigations | retrieved memory includes version, trust tier, created/updated time; never treated as current runtime state |
| `git_ci` | GitHub commits, checks, workflows | diffs, build outcomes, regression history | immutable commit/check-run identifiers, fetched at query time or bounded cache |
| `runtime` | Kubernetes API and monitoring backends | pods, deployments, events, health, observed dependencies | live mode requires observation within max_age_seconds; timeouts yield gaps |
| `telemetry` | logs, metrics, traces, event bus | incident timelines and failure correlation | explicit time window, source timestamp and clock-skew handling |
| `policy` | claim-gate, rules and current issue claim records | ownership, scope, applicable policy | live policy decision; never infer permission from semantic search |
| `evidence` | Aevum/claim checker | verified receipts, reproducible measurements | validate relevant proof with bound subject and verifier; report unverifiable separately |

**Rollout sequencing:** `code + catalog + memory` first (already implemented to varying degrees); then `git_ci + runtime`; then `telemetry + evidence`. Do not assume a connector exists merely because a deployment YAML exists. Each adapter has a separately verified access path.

## 5. Deterministic context compilation algorithm

1. Validate schema, authenticate principal, resolve tenant/scope, and apply broker policy.
2. Classify intent using deterministic signals and optionally a bounded model classifier only when ambiguous. A model cannot grant authorization or freshness exemptions.
3. Create a retrieval plan listing required and optional adapters. Example: `runtime_diagnosis` requires runtime observations; `code_navigation` requires code index.
4. Query adapters in parallel under a global deadline; enforce per-adapter fanout and concurrency. Collect candidate IDs, source timestamps and declared scores without comparing incomparable score scales.
5. Hydrate the top candidates *within each authority domain*. Reuse Gortex's order for code. Preserve structured graph edges and source excerpts.
6. Deduplicate by `(source_type, immutable_identity, revision, span)`; retain cross-source corroboration as separate evidence.
7. Detect source conflicts: same entity/property but differing values; retain both with observation times. Never choose a winner merely because semantic similarity is higher.
8. Apply authority ordering **per claim type**: live observed state > historical description for live questions; immutable code at requested commit > documentation for implementation questions; signed event > unsigned assertion for event-origin questions. No universal ranking across all claim types.
9. Allocate bounded tokens by source category, then compile deterministic ContextPlan and provenance envelope. Preserve existing plan hashing and source digest rules.
10. Return answerability/coverage and explicit missing sources. Answer generation, if requested, is a downstream consumer of the context envelope and must cite claim-support references.

**Caching:** cache keys include normalized query, intent, principal/scope hash, temporal mode, commit SHA or time bucket, adapter versions, policy revision, budget and schema version. No cross-principal cache reuse without explicit public classification. Invalidate code on new index manifest, catalog on projection revision, memory on write/version event, and runtime by TTL. Never serve expired live observations as fresh.

## 6. Security and epistemic acceptance

- **Prompt injection:** retrieved text is untrusted data; cannot issue tool instructions or override policy. Never concatenate retrieved instructions into the system policy channel.
- **Secrets:** scrub both adapter outputs and compiled response; preserve opaque secret references. Unit-test multiline and encoded secret variants; no claim that regex scrubbing is exhaustive.
- **Authorization:** perform scope enforcement before discovery and again on hydration; protect against path traversal, aliases, symlinks, tenant mixups and unauthorized cross-namespace graph edges.
- **Instrument execution:** `estate-claim-check` currently uses `bash -c`; no retrieved text may become a shell instrument. New context paths must use typed, allowlisted, sandboxed read-only probes with resource limits.
- **Claim binding:** do not promote a successful instrument to verified natural-language truth without a declared predicate, expected observation and provenance of the instrument itself.
- **Partial coverage:** a timeout, 403, stale index or missing source yields `PARTIAL` or `UNAVAILABLE`, never fabricated complete results.
- **Provenance:** all code references use immutable SHAs and line spans; all runtime observations include observed_at; all graph edges include declared/observed/inferred classification.
- **Cost:** maximum fanout, byte ceilings, token budgets, request deadlines, concurrency quotas and cache metrics are mandatory.

## 7. SLOs and release thresholds (proposed targets, not measured baselines)

**Pilot workload:** 100 curated questions covering code, architecture, deployment, incidents, policy, memory and multi-hop impact; at least 20 adversarial cases (stale documentation, wrong service, conflicting timestamps, malicious retrieved instructions, false passing checks).

| Measure | Pilot release threshold | Measurement |
|---|---|---|
| Critical authorization bypasses | 0 | negative integration and penetration tests |
| Stale response incorrectly marked live | 0 | forced index lag and runtime TTL expiry |
| Fabricated source identifiers | 0 | exact resolver verification |
| Required-source recall@20 | >= 0.90 | expert-labelled evidence sets |
| Supported factual claims with traceable source | >= 0.98 | claim-by-claim audit |
| Appropriate abstention on unanswerable cases | >= 0.95 | negative evaluation set |
| Deterministic compilation | 100% | same pinned inputs -> identical plan hash |
| Code-only p95 latency | <= 3s | warmed broker, representative queries |
| Federated p95 latency | <= 8s | mixed workload under pilot concurrency |
| Cost and token reporting | 100% requests | telemetry completeness |

These are **engineering acceptance criteria**, not forecasts. Adjust only after collecting baseline measurements; do not weaken correctness to meet latency.

## 8. Release programme / dependency graph

**Phase 0 — Reality audit (blocking):** Obtain CI runs, broker pod health, index manifest SHA, Gortex tool catalog, memory embedding health, catalog freshness, agentgateway route, actual consumer inventory, resource budgets. Execute existing tests and context gate. Deliver a signed baseline report with PASS/FAIL/BLIND per surface. **Exit:** all claimed existing capabilities have observed runtime or CI evidence; unknowns are explicit.

**Phase 1 — Contract and fixtures:** Implement response schema and source adapters' interface *without* changing current `estate_context`; build golden fixtures and adversarial tests. **Exit:** deterministic plan hashes, strict validation, no leaked secrets, zero unauthorized results.

**Phase 2 — Code/catalog/memory pilot:** Reuse existing Gortex engine, Backstage projections and unified memory. Implement deterministic cross-domain merging and coverage reporting. **Exit:** curated pilot thresholds met; old MCP tool unchanged.

**Phase 3 — Runtime and CI:** Add read-only GitHub/CI and Kubernetes adapters; bind live claims to observation time and resource UID. **Exit:** live/stale failure injection, access controls and p95 thresholds pass.

**Phase 4 — Telemetry, events and proof:** Add time-bounded logs/traces/events and proof retrieval. Correct semantic verification promotion before enabling verified answer labels. **Exit:** incident reconstruction and contradiction benchmarks pass.

**Phase 5 — Consumer migration:** Shadow-run Oracle and agent context calls; compare results and budgets, then canary by agent/surface with rollback. **Exit:** no regression against current code-context path, cost/latency within budgets, explicit consumer coverage.

**Phase 6 — Operational closure:** dashboards, runbooks, alerting, reindex failure handling, index artifact retention, access review, backup/restore, chaos tests and continuous evaluations. **Exit:** evidence of recovery from missing index, unavailable memory, unreachable Gortex, stale runtime, revoked permissions, and corrupted cache.

**No new database by default.** Add persistent technology only after a measured inability of Gortex, unified memory, existing catalog graph and event stores to meet an acceptance criterion.

## 9. Concrete repository changes proposed

All paths below are proposed; use the estate's issue/CLAIM/lane workflow before writing.

- `platform/estate/context/contracts.py`: versioned request, evidence, coverage and response models.
- `platform/estate/context/adapters/base.py`: typed adapter protocol and cancellation/deadline contract.
- `platform/estate/context/adapters/{code,catalog,memory}.py`: adapters around existing authorities, no duplicated indexes.
- `platform/estate/context/federation.py`: deterministic query planning, fanout, dedup, authority and budget handling.
- `platform/estate/context/server.py`: register `estate_context_resolve_v1`; preserve current tools.
- `platform/estate/context/broker.py`: extend policy to typed scopes and source-level authorization, preserving existing checks.
- `tests/context/`: schema, golden, negative, property, mutation, authorization, stale-index, timeout and source-conflict tests.
- `eval/estate-context/`: benchmark questions, labelled evidence sets, scorer and baseline reports.
- `platform/mcp/estate-context-broker.yaml`: only add env/secret/resource changes supported by measured deployment needs.
- `docs/runbooks/estate-context-substrate.md`: operations, degraded modes and rollback.

## 10. Mandatory test matrix

| Scenario | Expected outcome |
|---|---|
| Gortex index SHA differs from requested commit | REFUSED/STALE for commit mode |
| Working-copy index behind HEAD | labelled ASYNC_REINDEX, never presented as fresh commit proof |
| Memory server unavailable, code source available | PARTIAL; code preserved, memory gap explicit |
| Runtime source unavailable for live health question | UNAVAILABLE or PARTIAL with live status UNKNOWN |
| Retrieved document contains fake system instructions | treated as data; no action/tool invocation |
| User lacks repository or namespace scope | REFUSED before retrieval, no candidate leakage |
| Graph edge joins entities from unauthorized namespaces | edge omitted; gap or refusal recorded |
| Code and stale docs contradict | source-attributed conflict; implementation sourced from pinned code |
| Same input/revision/budget twice | identical context plan and plan_hash |
| Cache populated under privileged principal then queried by unprivileged one | no privilege leakage |
| Claim checker instrument succeeds but does not test proposition | UNVERIFIED, never REEXECUTED |
| Aevum unavailable or exported verification flag forged | proof status UNKNOWN/UNVERIFIED, not trusted |
| One adapter exceeds deadline | partial response within global deadline |
| Context output exceeds budget | deterministic omission/refusal, no silent truncation |
| Canary produces worse source recall or unauthorized results | automatic rollback to existing `estate_context` path |

## 11. Operations, ownership and rollback

**Ownership:** broker owns policy/response envelope; Gortex owns code ranking/index; unified memory owns memory records and semantic memory search; catalog owns declared topology; runtime adapters read authoritative runtime APIs; Aevum owns signed evidence. No shared write credentials across these domains.

**Observability:** emit request count, status, latency per adapter, cache hit, source coverage, stale/refused counts, index lag, redaction count, plan tokens, cost, unsupported claim rate. Include correlation ID but never secrets or full confidential payloads.

**Deployment:** feature flag new MCP tool; shadow mode; 5% canary; 25%; 100% only after gates. Retain old `estate_context` and immutable index artifacts. Rollback disables the new tool and adapter traffic, without migrating or mutating authoritative stores.

**Failure policy:** read-only code navigation may degrade to pinned source inspection if the broker explicitly supports that policy; live state queries must not degrade to historical memory while claiming freshness. Authorization uncertainty always refuses.

## 12. Unresolved questions requiring live inspection before code changes

1. Is `estate-context-broker` deployed, reachable through agentgateway, and exercised by Claude/Pi/other consumers?
2. What was the latest `context-index` workflow result, and which commit/OCI digest is deployed?
3. Which repositories and branches are actually indexed, and what is the measured index lag?
4. Is unified memory embedding/search healthy, and are memory records scoped by caller identity?
5. What are the existing runtime, CI, topology and telemetry API contracts and auth scopes?
6. What is the exact installed Gortex tool catalog, and which graph features are already usable?
7. Which agent tools currently bypass the broker, and what policy applies to non-editing read access?
8. What CPU/RAM/storage/network ceilings are available for production federation and cache?
9. Does the existing context gate pass against the current `main` and live deployment?
10. Which operational questions have verified reference answers suitable for a benchmark?

**No claim of shipping readiness is justified until Phase 0 is complete.** This RFC specifies an incremental build that can be shipped without duplicating the existing context engine; the outstanding work is to establish operational reality and then close measured gaps.



---

## SOURCE 2: Context Production Certification

**Original file:** `IDP_Production_Certification_Implementation_Plan_v1.md`

**Preservation:** complete source text follows.

# IDP estate context substrate — production certification and implementation plan v1

**Date:** 2026-10-28  | **Repository:** `chidionyema/idp`  | **Inspected main commit:** `2285593f0a4da6c3aebb895a1e55cd3fcf6eee83`  | **Status:** release-candidate specification; **NOT production-certified**.

This is an execution contract, not an assertion of deployment. Production certification is an outcome of the evidence gates below. Do not mark any gate PASS without attaching machine-verifiable results from the target environment.

## Decision

Extend the already implemented context stack, not a new RAG service. Retain Gortex as sole code-context ranker, `estate-context-broker` as the enforcement point, `ContextPlan` as deterministic compilation contract, unified memory as the memory authority, and catalog/affected-graph as topology sources. Add a versioned **federated read-only context API** to the existing broker with typed adapters and explicit coverage. Keep existing `estate_context` backward compatible. No new persistent database without benchmark evidence.

## 1. Code-grounded current state

| Component | Implementation | Production proof needed |
|---|---|---|
| Gortex index | `.github/workflows/context-index.yml` builds v0.64.11 index, tests freshness, publishes OCI artifact, signs it | Latest workflow run, index digest, signature verification, target pod index SHA |
| MCP broker | `platform/estate/context/server.py` exposes `estate_context` and `estate_context_status` | authenticated gateway end-to-end request; caller identity; trace |
| Policy | `platform/estate/context/broker.py` enforces tool allowlist, claims, freshness, budget, secret redaction | live refusal probes, negative auth tests |
| Deterministic compiler | `platform/estate/context/plan.py`, `bin/estate-context-compile` | deterministic hash across repeat executions with pinned inputs |
| Broker deployment | `platform/mcp/estate-context-broker.yaml` has loopback engine sidecar, index PVC | running image digests, resource usage, isolation and NetworkPolicy checks |
| Unified memory | `platform/unified-memory-server/main.py` exposes search, recall, brief, embeddings status | tenant isolation, embedding health, latency, recall quality |
| Topology | `bin/idp-affected-graph`, `bin/catalog-projection`, Backstage providers | coverage and edge ground truth |
| CI/test gates | `bin/estate-context-gate`, `tests/test_estate_context_{broker,compile,server,claims}.py` | test logs with SHA, exit code, runner and artifacts |

**Access limitation:** GitHub source and main commit were read through the connected repository. GitHub Actions workflow-run endpoint was rejected by the connector. Kubernetes, production metrics, deployment revisions, network access and live CI test results are not accessible through that read path. These are **BLIND**, not PASS or FAIL.

## 2. Production target: one federation contract

**New tool:** `estate_context_resolve_v1` on existing MCP broker; no mutation tools, no public Gortex route. Existing tools remain unchanged.

**Input:** `query`, `intent`, `scope`, `temporal` (`commit`, `as_of`, `live`), `evidence`, `limits` (`deadline_ms`, `token_budget`, `max_sources`), authenticated principal from gateway and optional issue/agent claim. Never trust client-supplied principal or trust tier.

**Output:** `schema_version`, `query_id`, `status` (`COMPLETE`, `PARTIAL`, `REFUSED`, `UNAVAILABLE`, `INVALID_REQUEST`), `context_plan`, `sources`, `claims`, `gaps`, `policy`, `timing`, `cache`. Every source has immutable revision or observed timestamp, locator, digest where applicable, authority, and evidence method. Every claim references its supporting source IDs. `SUPPORTED_SOURCE` must not be interpreted as semantic entailment; `REEXECUTED` requires a proposition-bound typed verifier.

**Typed adapters:** `code` (Gortex), `catalog` (catalog projection), `memory` (unified-memory API), `git_ci` (GitHub immutable commits/checks), `runtime` (Kubernetes read-only), `telemetry` (bounded logs/metrics/traces), `policy` (claim issue and effective policy), `evidence` (Aevum/verifier). Each implements `discover`, `hydrate`, `health`, deadline/cancellation, identity and scope validation. No arbitrary shell command from retrieved material.

**Compilation:** authenticate -> authorize scope -> classify intent -> select required/optional authorities -> parallel bounded discovery -> source-specific ranking -> hydrate -> deduplicate by source/revision/span -> compare conflicts -> deterministic budget allocation -> provenance and coverage envelope. Code ranking remains Gortex-owned; do not introduce a competing global embedding index.

**Freshness:** commit mode refuses index mismatch; live mode refuses to call stale cached data live; working-copy mode may explicitly report `ASYNC_REINDEX` as already supported by broker. Cache key includes principal/scope, revision, policy version, query, schema and budget. Revocation invalidates authorization regardless of cache TTL.

## 3. Critical dependencies and implementation work packages

| ID | Prerequisite | Change set | Required tests | Exit |
|---|---|---|---|---|
| P0 | none | Baseline collector and evidence manifest; run existing gates and live probes | existing context suite + reproducibility of collector | signed baseline with no unexplained BLIND for claimed capabilities |
| P1 | P0 | `platform/estate/context/contracts.py` typed schemas; fixtures; backward compatibility tests | strict schema, malformed input, unknown scope, downgrade tests | no change to existing tool responses |
| P2 | P1 | `platform/estate/context/adapters/{base,code,catalog,memory}.py`; `federation.py` | auth before discovery and hydration, stale index, memory down, conflicting sources, determinism | source-linked answers, required-source recall@20 >=0.90 on labelled set |
| P3 | P2 | Register `estate_context_resolve_v1` in `server.py`, enforce via `broker.py` | end-to-end MCP protocol, auth, path traversal, symlink, cross-tenant, secret leak | zero critical bypasses; old endpoint unchanged |
| P4 | P3 | `git_ci` and `runtime` adapters with read-only credentials | CI SHA pinning, RBAC denial, stale observations, cluster API outage | no cached history masquerading as live state |
| P5 | P4 | telemetry, policy and evidence adapters; semantic verification boundary | malicious retrieved instructions, false passing instrument, forged export flag, timestamp conflict | no false verified claims in adversarial suite |
| P6 | P5 | shadow consumers (Oracle, Claude, Pi), canary routing and dashboards | diff against baseline, load, chaos, rollback | acceptance thresholds and rollout gates all PASS |

No P2–P6 code should be merged on speculative assumptions about deployed infrastructure. Gate each dependency in sequence; independent tests can run concurrently.

## 4. Baseline capture: exact operator commands

Run from a clean checkout at a pinned SHA. Save all stdout/stderr, UTC timestamps, exit codes and SHA-256 digests in the release evidence bundle. These commands are **proposed**, not executed in this review.

```bash
set -uo pipefail
mkdir -p artifacts/context-cert
{
  date -u +%Y-%m-%dT%H:%M:%SZ
  git rev-parse HEAD
  git status --porcelain
  python3 --version
} > artifacts/context-cert/environment.txt

python3 -m pytest -q \
  tests/test_estate_context_broker.py \
  tests/test_estate_context_compile.py \
  tests/test_estate_context_server.py \
  tests/test_estate_context_claims.py \
  > artifacts/context-cert/pytest.log 2>&1
printf '%s\n' "$?" > artifacts/context-cert/pytest.exit

python3 bin/estate-context-gate \
  > artifacts/context-cert/context-gate.log 2>&1
printf '%s\n' "$?" > artifacts/context-cert/context-gate.exit

gh run list --workflow context-index.yml --limit 10 --json databaseId,headSha,status,conclusion,createdAt,url \
  > artifacts/context-cert/context-index-runs.json

kubectl -n mcp get deploy,pods,svc,pvc -l app.kubernetes.io/name=estate-context-broker -o json \
  > artifacts/context-cert/broker-resources.json
kubectl -n mcp get deploy estate-context-broker -o yaml \
  > artifacts/context-cert/broker-deployment.yaml
kubectl -n mcp get pods -l app.kubernetes.io/name=estate-context-broker -o json \
  > artifacts/context-cert/broker-pods.json
```

**Safety:** production commands above are read-only. The working directory `artifacts/context-cert` is local; do not commit raw environment output before reviewing secrets, private topology and access controls. A missing `gh`, `kubectl`, kube context or permissions yields BLIND with reason. Do not attempt unauthorized credentials or mutate production to make a probe pass.

**Further required operator observations:** (a) authenticated `estate_context_status` via actual agentgateway route, (b) one authorized and one unauthorized MCP request with redacted transcripts, (c) actual index `index.json` commit and OCI digest + cosign verification, (d) `/embeddings/status` via permitted memory route, (e) catalog projection age, (f) service RBAC and namespace policies, (g) resource requests/limits and measured p95 latency. Save raw evidence securely and summarize redacted results.

## 5. Certification matrix — all are release blockers unless expressly waived

| Gate | Test / evidence | Pass criterion | Initial status |
|---|---|---|---|
| C01 provenance | clean SHA + reproducible build + immutable OCI digest | source, image, index and signature match | BLIND |
| C02 CI | context gate and targeted tests | all required tests PASS, no skipped critical checks | BLIND |
| C03 transport | authenticated MCP through gateway | valid protocol, caller identity preserved, private engine unreachable | BLIND |
| C04 authorization | negative principal/tenant/path tests | zero unauthorized retrieval or cache leaks | BLIND |
| C05 freshness | stale index and expired runtime observations | zero stale results labelled current | BLIND |
| C06 evidence integrity | source hashes, revision, timestamps | zero invented references or unsupported verified labels | BLIND |
| C07 determinism | repeated pinned query and source set | identical plan hashes, omission list and ordering | BLIND |
| C08 retrieval quality | 100 expert-labelled questions, >=20 adversarial | recall@20 >=.90; supported claims >=.98; abstention >=.95 | BLIND |
| C09 performance | representative warmed and cold load tests | code-only p95 <=3s; federated p95 <=8s; limits respected | BLIND |
| C10 resilience | missing index, engine down, memory down, 403, timeout | correct REFUSED/PARTIAL/UNAVAILABLE; no false COMPLETE | BLIND |
| C11 operations | dashboard, alert, runbook, on-call and rollback drill | recovery evidenced; no data-loss or auth bypass | BLIND |
| C12 rollout | shadow diff, 5%, 25%, 100% stages | each stage meets gates, no regression vs legacy tool | BLIND |

Thresholds are **proposed release criteria**, not observed SLOs. Baseline results may justify stricter thresholds; any relaxation requires an explicit recorded decision and risk owner. Security, provenance and stale-as-live failures are not waivable for production certification.

## 6. Evaluation corpus and scoring

Store at `eval/estate-context/` with versioned fixtures, provenance and gold evidence. Stratify 100 cases: 20 code, 15 dependency/impact, 15 runtime, 15 incident, 10 memory/decision, 10 CI/GitOps, 10 policy/security, 5 cross-domain. At least 20 adversarial cases distributed across categories: stale docs, incorrect test name, counterfeit source URL, injected tool instruction, unauthorized namespace, cross-principal cache, false-positive instrument, missing runtime, conflicting observations, truncated response. Each case specifies required authoritative sources, forbidden assertions, expected abstention/coverage, maximum age and a deterministic grader. Human adjudication for ambiguous causal claims; no self-grading by the same generation model as sole oracle.

Report recall@20, citation validity, claim support precision, appropriate abstention, source coverage, contradiction detection, latency p50/p95/p99, CPU/RAM, index size, token usage and cost per question. Compare existing `estate_context`, federated implementation and a source-only deterministic baseline. Benchmark on a pinned commit and repeat on a changed commit to measure index lag and staleness.

## 7. Deployment, rollback and operational constraints

- Package in existing broker image; maintain loopback Gortex sidecar and existing private network boundary.
- Feature flag the new MCP tool; default disabled until C01–C11 PASS. Shadow invocation must not leak protected data or change any source of truth.
- Canary progression: internal authorized consumer -> 5% -> 25% -> 100%; minimum 24-hour observation per stage **proposed**, adjust only with measured traffic volume. Automatic rollback on any auth leak, stale-as-live claim, source fabrication, sustained error-budget burn or index provenance failure.
- Rollback: disable the new tool/route and adapter fanout; preserve old `estate_context`; revert broker image to recorded digest; leave memory, catalog, Git and Kubernetes untouched. Verify old MCP endpoint after rollback.
- Keep previous signed index artifact available; test loss of latest index and verify fail-closed behaviour for commit-pinned requests.
- Instrument adapter latency, errors, coverage, cache scope, redactions, plan tokens, authorization refusals, index lag and per-source freshness; use opaque request IDs and redact payloads.
- Capacity: enforce deadline, per-adapter concurrency, memory and CPU ceilings; establish actual node headroom before sizing. Do not assume the existing 2Gi index PVC is sufficient for new federated workloads.

## 8. Governance and sequencing

The repository's `AGENTS.md` requires a GitHub issue, an active CLAIM with covered paths and a `lane/*` branch; do not push directly to main or bypass Greenlane. Create one programme issue with child work items P0–P6, explicit owner, dependency and acceptance evidence. No agent should claim ownership of paths until the issue/claim mechanism confirms it. Release evidence must identify author, commit, test environment, runner, timestamps, exit codes and immutable artifact digests.

**Go/no-go decision:** production certification is `PASS` only if all C01–C12 are independently evidenced and the release owner approves the recorded manifest. Otherwise status is `NOT CERTIFIED` with blockers. This document is immediately usable to begin P0; it does not falsely assert that the estate has already met those gates.

## 9. Source references (repository, pinned main SHA above)

- `platform/estate/context/{broker,server,plan,claims,local_engine}.py`
- `bin/{estate-context-compile,estate-context-gate}`
- `.github/workflows/context-index.yml`
- `platform/mcp/estate-context-broker.yaml`
- `platform/unified-memory-server/{main,ranking}.py`
- `tests/test_estate_context_{broker,compile,server,claims}.py`
- `mcp/plugins/estate_memory.py`
- `AGENTS.md`

**Evidence note:** Source files were inspected through the connected GitHub repository. Current live GitHub Actions runs and cluster state have not been observed. Never promote source existence to operational certification.



---

## SOURCE 3: Autonomous Media Department

**Original file:** `IDP_Autonomous_Media_Department_Charter_v1.md`

**Preservation:** complete source text follows.

# IDP Autonomous Media Department — implementation charter v1

**Date:** 2026-10-28  **Repository:** `chidionyema/idp` **Inspected main:** `2285593f0a4da6c3aebb895a1e55cd3fcf6eee83` **Status:** PROPOSED; NOT DEPLOYED OR CERTIFIED.

## 1. Executive mandate

Establish an autonomous Media Department as the first reusable operating model for autonomous estate departments. Its remit spans live estate film, real-time virtual worlds, agent avatars, interactive product demonstrations, media production, research, prototyping, proposals, visual quality and operational maintenance. It must **discover work proactively, research, prototype, evaluate, propose, execute authorized changes, verify outcomes, and learn**. A recurring research report without a tested artifact is not a completed deliverable.

## 2. Non-negotiable estate constraints

1. `AGENTS.md` and `docs/epics/2026-10-25-estate-master-epic.md` are the programme authority: structured contracts, shared memory, evidence, metric-driven improvement, named deciders and no duplicate infrastructure.
2. ADR `docs/decisions/0037-the-film-is-a-deterministic-twin-of-the-event-spine.md` is **accepted**. Live estate film is a deterministic projection of actual events. No generative video in the core truth path. Generative media is permitted only as a separately labelled optional creative/export lane, subject to new governance decisions where needed.
3. `docs/specs/2026-10-23-estate-as-movie-director-engine.md` establishes the scene contract, voice causality, real artifact pane, Fleet/Face surfaces, S0–S4 and rollback criteria. `docs/research/2026-10-25-virtual-world-vs-realtime-film.md` establishes virtual worlds as a *second renderer* of the same scene contract, not an alternative source of truth.
4. Reuse existing NATS JetStream, Temporal, Dagster, estate-execute, claim/approval doors, context broker, unified memory, Fleet, Face and research engine. New tools require measured superiority and an integration/removal plan.
5. The department must not publish, spend beyond cap, modify production, impersonate an agent, or issue a live steering command without existing policy authorization.

## 3. Research findings and selection rules

- Google Research, 2026-09-24, *Automating coherent long-form video generation*: hierarchical multi-agent pre-production, keyframe/video/audio specialists, continuity tracking and closed-loop multimodal judging. Adopt **planning and evaluation patterns**, not generative footage for live estate truth. https://www.research.google/blog/coherent-long-form-video-generation/
- NVIDIA, 2026-09-16, *How to Use AI Agents to Prepare 3D Scenes for Simulation*: Blender MCP, OpenUSD, semantic labels, physics, visual preflight and SimReady validation. Candidate for *offline authoring and simulations*; not a reason to install a GPU-heavy live world stack. https://developer.nvidia.com/blog/how-to-use-ai-agents-to-prepare-3d-scenes-for-simulation/
- OpenAI Agents SDK: tracing, specialist handoffs and durable Temporal integration. Reuse estate Temporal as orchestrator rather than create a competing workflow service. https://openai.github.io/openai-agents-python/running_agents/
- Existing repo comparison: Three.js (already used in Fleet) as first renderer; three-vrm only if character fidelity is required; Colyseus only if authoritative multiplayer state is proven necessary; Playwright as the real-browser truth anchor; Blender/OpenUSD as offline asset format; optional generated clips via model-neutral provider adapter after benchmark/licence review.
- Prior research-engine failure is concrete: `platform/research-engine/objective-adapter.py` documents a wrong research lane producing zero admitted claims, and requires founder Continue/Park. The new department must autonomously advance **within bounded delegated authority** and terminate in experiments, proposals and measurable outcomes rather than passively waiting after a report.

## 4. Reusable department operating contract

`Objective -> Opportunity -> Hypothesis -> ResearchEvidence -> ExperimentPlan -> PrototypeArtifact -> IndependentEvaluation -> Proposal -> GovernedChange -> ProductionVerification -> Outcome -> Learning`

Mandatory envelope on every artifact/event: `schema_version`, `department_id`, `objective_id`, `run_id`, `parent_run_id`, `kind`, `state`, `source_ref`, `source_revision`, `evidence_refs`, `artifact_uri`, `artifact_sha256`, `created_at`, `expires_at`, `authority`, `policy_decision`, `budget_cap_usd`, `spend_usd`, `evaluator_id`, `verdict`, `reason`. Nullable fields must be explicitly declared by schema and validated at the relevant transition. Never accept an untrusted generated assertion as a production observation.

States: `NEW, TRIAGED, RESEARCHING, PROTOTYPING, EVALUATING, PROPOSED, APPROVED, SHIPPING, VERIFYING, OPERATING, LEARNING, BLOCKED, PARKED, REJECTED`. The runtime enforces legal transitions. No `RESEARCHING -> SHIPPING`; no `PROPOSED -> APPROVED` without the existing authorization door; no `VERIFYING -> OPERATING` without independent evidence.

**Execution model:** a single durable department workflow instantiated by configuration; typed task queues and capability-scoped workers. Agents are replaceable workers, not independent organizations. Each action names its decider and writes an immutable run/event reference. Queueing is idempotent by `(objective_id, action_kind, input_revision)`. Retry with exponential backoff and finite maximum; poison items go to an existing dead-letter mechanism; cancellation propagates. Enforce per-objective and per-day budgets, concurrency and time ceilings at the existing router/execution boundary. A verifier cannot certify its own prototype.

## 5. Department capabilities

| Capability | Inputs | Concrete output | Gate |
|---|---|---|---|
| Portfolio governor | Founder objectives, estate signals, observed gaps | Ranked bounded opportunity queue | Objective provenance, budget, no duplicates |
| Research scout | Versioned research questions, web/repo sources | Source-linked comparison, falsifiable hypothesis | Source quality, currency, relevance |
| Technical/creative director | Scene contract, user goals | Storyboard, shot grammar, world interaction plan | Causal truth, feasibility |
| Prototype studio | Approved experiment plan, sandbox | Working code/demo, visual capture, digest | Sandbox, licences, reproducibility |
| Independent evaluator | Prototype, acceptance fixtures | Structured scorecard, adversarial results, verdict | No self-approval |
| Delivery and operations | Approved proposal | Governed PR, deployed artifact, rollback record | CI, policy, live smoke test |
| Learning loop | Runtime outcome and cost | Updated experiment record and future policy proposal | Measured delta, provenance |

## 6. Flagship acceptance scenario

Founder opens Fleet and sees an avatar accurately representing an agent's *actual* work; speaks a directive; the existing voice/intent gate changes the agent's real work; the world shows the resulting real task, test, commit and deployment transitions; the founder opens a genuine deployed URL in a real browser; the sequence replays deterministically as film. Avatar animations without backing event IDs are forbidden. A screenshot is never a substitute for the real running application. Promotional generative footage, if produced, is labelled and isolated from the live state renderer.

## 7. Work packages, owners, evidence and release gates

### M0 — Measured baseline (no new runtime)
Inventory actual code, active workloads, tests, GitHub issues, past research/science department failures, event contracts, Fleet/Face hooks, runtime resource ceilings, and existing media dependencies. Capture source SHA, command outputs, observed caller graphs and deployment status. **Pass:** a machine-readable capability matrix with `implemented`, `observed_live`, `tested`, `unknown` and `broken` fields, and a ranked non-duplication gap list. Never infer deployment from YAML.

### M1 — Department contract and BDD
Add versioned JSON Schemas for objective, opportunity, experiment, artifact, review, decision, outcome and event; deterministic state machine; compatibility/migration policy. **Pass:** tests reject missing source refs, illegal transitions, budget overflow, stale provenance, duplicate idempotency keys and unauthorized writes.

### M2 — Durable autonomy runtime
Integrate existing Temporal/Dagster and JetStream, router budgets, issue/claim workflow and estate-execute. Configure signal subscriptions and scheduled scans with backpressure, dedupe, finite retries, cancellation and pause/kill switch. **Pass:** same input replay does not duplicate PRs, expenditure or publication; restart resumes safely; poison work does not block other objectives.

### M3 — Media studio and scene renderers
Integrate existing Go director and scene contract with Fleet/Face; prototype one browser-native agent/avatar scene using Three.js and real event-driven state; attach real Playwright browser proof. **Pass:** deterministic replay of ordered events; stale/out-of-order and fabricated events refused; actual founder directive correlated to downstream intent and result; graceful degraded mode when stream is unavailable.

### M4 — Research/prototype loop
Automatically identify one estate media gap, compare at least three candidate implementations (including doing nothing), execute one bounded prototype and produce a scored, inspectable proposal. **Pass:** independently runnable prototype, source citations, asset licences, measured latency/cost, known failure modes and a justified recommendation. A text-only report fails.

### M5 — Independent grading
Visual regression, narrative/scene continuity, event-to-avatar fidelity, accessibility, browser evidence, adversarial prompt injection, budget, licensing, recovery and SLO tests. **Pass:** no false positive for fabricated agent activity, missing authorization or unverified deployment. Human aesthetic judgment is an explicit review signal, not a fabricated numeric proof.

### M6 — Operate and learn
Expose a department page in Fleet/Face with objective queue, experiments, live run state, blockers, costs, prototypes, proposal decisions, deployments and outcome deltas. Monitor failure, backlog, budget, stale evidence and unattended liveness. **Pass:** a scheduled/event-driven unattended run progresses from objective to real evaluated prototype and proposal; approved change goes through governed shipping and outcome tracking; a rollback drill succeeds.

### M7 — Prove reusable department spine
Instantiate Research and Science in shadow mode with the same schemas/workflow/gates but their own evaluators and policies. **Pass:** both generate executable experiments with outcome measurements, no parallel scheduler/ledger/approval stack and no false operational status.

## 8. Initial proposed SLOs (validate against M0 baseline)

- 100% live avatar activity linked to real event IDs and revisions; 0 fabricated production states.
- 100% unauthorized tool/action requests refused at the authoritative execution boundary.
- 0 duplicate externally visible effects under retry and replay fixtures.
- 100% deterministic replay equivalence for core scene outputs (exact schema-defined equivalence).
- 100% proposals include executable artifact, independent scorecard, cost and source references.
- First evaluated prototype proposal within 24 hours of a bounded accepted objective *where budget, source access and capacity are available*.
- No uncapped external API spending; no indefinite retries; explicit pause/kill and rollback.
- Record baseline-to-treatment deltas for research time, prototype success, cost per accepted proposal and founder intervention count.

## 9. Certification evidence packet

For each gate store: immutable source revision, workflow run ID, test command and exit code, logs, signed/digested artifacts, independent evaluator identity, deployment identity, observed smoke test, cost and latency measurement, security result, rollback drill and final decision. **Production certified** is a computed result over evidence, not a manually assigned label. Fail closed for unsupported production claims; remain useful in read-only/degraded mode.

## 10. Governance and initial action

Before modifying repository code, create a GitHub issue, acquire the AGENTS.md claim/heartbeat, inspect concurrent work and use `lane/<name>` branches with `estate-execute lane-submit`. First PR: M0 baseline + M1 schemas and BDD only. No direct push to `main`.

**Current access blocker:** attempted to create the governing issue via the connected GitHub app on 2026-10-28; GitHub returned `403 Resource not accessible by integration`. The issue has **not** been created, no repository changes have been made, and no live workloads have been started. Granting GitHub Issues write permission or executing the issue creation through an authorized estate agent is required to initiate the governed implementation lane.

## 11. Definition of done

The Media Department is a persistent, bounded, observable autonomous operating capability that independently discovers and evaluates opportunities, produces working media artifacts, requests authorization only where policy requires, ships via estate gates, measures real-world outcomes and feeds lessons back into shared context/memory. A second department uses the same spine without copying infrastructure. No operational claim is made without execution evidence.



---

## SOURCE 4: Commercialisation / Special Forces

**Original file:** `Estate_Special_Forces_Operationalisation_Spec_v1.md`

**Preservation:** complete source text follows.

# Estate Special Forces — Full Operationalisation Specification v1

**Date:** 2026-10-28  
**Target repository:** `chidionyema/idp`  
**Status:** IMPLEMENTATION-READY SPECIFICATION; NOT DEPLOYED OR CERTIFIED  
**Mission:** Progressively commercialise verified estate capabilities without creating a parallel platform or disrupting the existing transformation.

## 1. Mandate and strategic objective

Establish Special Forces (SF) as a **persistent, bounded, cross-functional autonomous intervention capability**, not a new organisation chart or multi-agent chat room. Its outcome is the first successful paid external invocation of an estate capability, followed by repeatable delivery, positive unit economics, and expansion to a second capability. SF should demonstrate the estate's reusable autonomous-department operating contract rather than inventing its own workflow engine.

**North-star event:** an external customer, authenticated under a tenant identity, invokes a documented estate capability; the system produces a verifiably correct deliverable; the customer accepts the result; payment settles; the event is linked to cost, policy, evidence and support records. No synthetic transaction counts as market validation.

**Explicit non-goals:** new agent framework, new scheduler, new message bus, new context store, direct public access to internal estate control planes, unsupervised production mutation, broad commercial portal before a verified demand signal, speculative billing infrastructure before a paid use case.

## 2. Source authority and existing estate alignment

- `AGENTS.md`: programme authority, seven reasoning gates, one-of-each-layer, claim/lane governance, intent-only execution, proof over assertion, named decider.
- `docs/epics/2026-10-25-estate-master-epic.md`: autonomy, coherent closed loops, proactive/event-driven work, metric-led improvement, founder go/no-go at strategic boundaries.
- `platform/estate/context/server.py`: existing MCP policy gateway pattern; it is **not** evidence of commercial multi-tenant readiness.
- Existing estate capabilities to inspect and reuse: GitHub issue/CLAIM/lane-submit, `estate-execute`, agentgateway, NATS JetStream, Temporal, Dagster, unified memory, context broker, catalog/capability-index, verification/evidence, router/budgets, Fleet/Face.
- `platform/research-engine/objective-adapter.py`: prior failure pattern of wrong-lane zero-claim research and passive Continue/Park; SF must deliver experiments, not report-only output.
- The Media department charter offers a compatible department envelope, but is proposed, not a running dependency.

**Authority levels:** founder-approved strategic mandate > policy/identity/execution decisions > verified tool observations > source-linked research > model hypotheses. Lower-trust text never grants execution authority.

## 3. Operational topology

```text
Founder strategy / external market / estate capability signals
                         |
              Opportunity intake adapter
                         |
       Deduplication + portfolio scoring + budget gate
                         |
             Durable mission controller
                         |
  Recon -> Hypothesis -> Prototype -> Independent evaluation
                         |
             Decision: kill / park / propose
                         |
          Existing claim + governed execution
                         |
        External sandbox -> pilot -> paid outcome
                         |
        Measured learning -> portfolio reprioritisation
                         |
                Fleet/Face visibility
```

**Six functions, dynamically assigned:** (1) mission commander/portfolio optimizer, (2) market reconnaissance, (3) estate capability pathfinder, (4) prototype/engineering operator, (5) independent verifier and security reviewer, (6) commercial validation and economics analyst. These are responsibilities, not six permanently running agents. A role can be staffed by deterministic code, existing estate agents or a specialist model. The verifier must be independently instantiated and cannot approve its own changes.

**Single accountable mission controller:** runs on existing durable workflow infrastructure selected after baseline. Scheduling uses the existing estate scheduler; events use the existing event bus; agent calls use existing router; state and evidence use existing stores. If a required adapter does not exist, add only an adapter, not a new infrastructure tier.

## 4. Mission contract (versioned schema)

Every mission carries:

```json
{
  "schema_version": "1.0",
  "mission_id": "uuid",
  "objective_id": "source-qualified-id",
  "department_id": "special-forces",
  "mission_kind": "recon|prototype|integration|pilot|commercial_validation|hardening",
  "problem_statement": "string",
  "customer_segment": "string|null",
  "hypothesis": "falsifiable statement",
  "success_metrics": [{"name":"string","baseline":null,"target":null,"unit":"string","evidence_source":"string"}],
  "authority_ref": "policy or founder mandate ref",
  "risk_tier": "R0|R1|R2|R3",
  "scope": {"repositories":[],"capabilities":[],"tenants":[],"environments":[]},
  "budget": {"max_usd":0,"max_wall_minutes":0,"max_agent_calls":0,"max_concurrent_tasks":0},
  "idempotency_key": "stable-key",
  "source_revision": "immutable revision",
  "dependencies": [],
  "artifacts": [],
  "evidence_refs": [],
  "state": "DISCOVERED",
  "decider": "identity",
  "created_at": "RFC3339 timestamp",
  "expires_at": "RFC3339 timestamp"
}
```

The example is an illustrative contract, not a validated final JSON Schema. Build strict JSON Schema definitions and migration tests in the first implementation slice. Every artifact has digest, creator, source, timestamp, authority and retention class. No fabricated provenance or self-declared `CERTIFIED` field.

### Mission lifecycle

`DISCOVERED -> TRIAGED -> HYPOTHESIS -> RESEARCHING -> EXPERIMENT_APPROVED -> PROTOTYPING -> EVALUATING -> PROPOSED -> GOVERNED_DELIVERY -> VERIFYING -> PILOT -> COMMERCIAL_VALIDATION -> OPERATING -> LEARNING -> CLOSED`

Any nonterminal state may transition to `BLOCKED`, `PARKED`, `CANCELLED` or `FAILED` through a recorded policy decision. `EVALUATING -> PROPOSED` requires independent evidence; `PROPOSED -> GOVERNED_DELIVERY` requires the estate's existing authorization path; `VERIFYING -> PILOT` requires tenant isolation and security gates; `PILOT -> COMMERCIAL_VALIDATION` requires explicit customer consent and contractual controls. No direct `RESEARCHING -> SHIPPING` shortcut. Resume only from checkpointed state; replay must not duplicate effects.

## 5. Autonomous opportunity discovery

**Sources:** founder objectives; existing estate capability index and catalog; observed internal pain (repeat incidents, manual founder intervention, expensive agent calls); customer requests; market research; external agent ecosystem interfaces; measurable gaps in documentation, API accessibility, identity, isolation, billing and verification.

**Discovery rules:** source-linked and timestamped; do not mistake speculative market commentary for customer demand; deduplicate by capability/problem/segment; expire stale opportunities; maintain negative findings; cap external searches and model spend; do not autonomously scrape private data or contact customers without authorization.

**Prioritization:** deterministic weighted score with configurable weights: validated customer pain (30%), reuse of existing estate capability (20%), time to independently verified pilot (20%), expected contribution margin (15%), strategic learning value (10%), integration risk (5% inverse). Score each dimension 0–5 with source-linked justification; missing customer evidence scores zero rather than invented confidence. The weights are starting hypotheses, not proven optimal. Use portfolio diversity and capacity constraints to prevent a single speculative mission monopolizing work.

**Selection:** one active build mission initially, up to two read-only reconnaissance missions; WIP limits enforced. Reprioritize on new evidence, objective expiry, critical incidents or explicit founder redirection. Suspend nonessential work during estate incident or CI degradation according to existing policies.

## 6. Delegated authority and risk

| Tier | Examples | Default action |
|---|---|---|
| R0 | Public-source research, read-only estate inventory, analysis | Autonomous within budget |
| R1 | Isolated sandbox prototypes, test fixtures, local documentation changes | Autonomous with bounded runtime and security constraints |
| R2 | PR creation, staging integration, customer sandbox provisioning | Existing claim, CI, review and policy gates; approval per existing estate rules |
| R3 | Production writes, external publishing, customer commitments, charging cards, secrets, legal terms | Explicit authorized approval; fail closed |

No role can mint its own authority. Customer-provided repositories, prompts and webhook payloads are untrusted. Secrets never appear in research artifacts. Isolation and resource quotas must be enforced by infrastructure, not by prompt instructions. The founder can pause the whole team; the estate incident controller can preempt its workloads.

## 7. Commercial exposure options and product sequencing

**Wedge A (preferred first hypothesis): Verified Engineering Task API.** Customer connects a scoped test repository, submits an issue and receives a tested PR with evidence, limitations and cost. **Do not assume this is profitable or wanted**; test willingness to pay before building full billing. First run in isolated sandbox, never on an unbounded customer production repository.

**Wedge B:** Bring-Your-Own-Agent via governed MCP capabilities (context, diagnostics, verification, delivery). Test after Wedge A proves isolation, metering and authorization.

**Wedge C:** Autonomous Department as a Service, only after the reusable department runtime passes independent operation and cost gates.

**Commercial gateway requirement:** tenant-bound identity, per-tenant entitlements, authorization at every state-changing tool call, scoped repository credentials, isolated execution and memory, usage/cost attribution, audit/evidence delivery, idempotent metering, quota enforcement, revocation, data deletion/retention policy, support/incident boundaries, rate limits, versioned API/MCP contracts. Use existing gateway where appropriate; add tenant mediation without bypassing it. Cross-tenant leak is a stop-ship defect.

**Pricing experiments:** fixed-price accepted outcome vs reserved engineering capacity vs usage with minimum; compare gross margin and dispute rates. Model full cost = model + compute + retries + verification + human oversight + support + payment processing + refunds. Count unsuccessful attempts against internal cost; charge only according to explicit customer terms.

## 8. Reusable department spine

SF must use the same generic department envelope as Media/Research/Science: `Objective -> Hypothesis -> Experiment -> Artifact -> Independent Evaluation -> Governed Action -> Outcome -> Learning`. Department-specific capability packs supply prompts, deterministic tools, evaluators, policies and portfolio scoring. Shared core owns identity, workflow state, budgets, evidence, event schema and Fleet visualization. **No copied scheduler, approval engine, memory or ledger.**

The first implementation must expose a department instance descriptor (`department_id`, mission templates, allowed capabilities, triggers, evaluation packs, budgets, escalation matrix, visualizations, kill switch). Demonstrate portability with a second shadow-mode department without deploying a duplicate runtime.

## 9. Operational work packages (small independently mergeable PRs)

### SF-0: Evidence-based baseline and overlap audit
- Pin repository SHA and gather current issues/PRs, deployed gateway/workflows, capability index, estate execution and policy paths, prior research/science failure evidence, active CI health and budget/observability state.
- Enumerate commercial-capability gaps and current callers. Classify `SOURCE_ONLY`, `TESTED`, `DEPLOYED`, `OBSERVED`, `UNKNOWN`, `BROKEN`.
- Deliver machine-readable inventory, architecture map, nonduplication analysis and initial benchmark.
- **Exit:** no ungrounded deployment claim; 100% proposed dependencies linked to real source or explicit unknown.

### SF-1: Mission schema, state machine and BDD
- Strict schemas for mission, evidence, experiment, proposal, authorization, outcome and learning.
- Deterministic transition guard, idempotency key, expiry, budget and policy validation.
- **Exit:** tests reject missing provenance, forged approval, illegal transition, duplicate effect, stale source, overspend, cross-tenant scope and self-certification.

### SF-2: Durable autonomous controller
- Existing scheduler + Temporal/Dagster adapter, event triggers, bounded retry, timeout, cancellation, backpressure, recovery and dead-letter behavior.
- Persist objective state and checkpointed tool effects with correlation IDs; emit trace/event references.
- **Exit:** kill/restart/replay drills; no duplicate PR, billing event or external call under retries; no unbounded run.

### SF-3: Reconnaissance and hypothesis laboratory
- Capability/market scan, scored opportunity queue, competitor and user problem evidence, explicit alternatives including do-nothing.
- Produce falsifiable experiment plan with budget, success threshold and failure threshold; sandbox prototype required before proposal acceptance.
- **Exit:** one real, independently reproduced prototype with code and scorecard; no report-only completion.

### SF-4: Governed commercial boundary
- Minimum external tenant sandbox, scoped identity, authorization, repository isolation, versioned REST or MCP surface, metering and evidence return.
- Do not expose internal gateway/engine directly; support revocation and abuse controls.
- **Exit:** negative isolation/security suite passes, including prompt injection and cross-tenant tests; authenticated external sandbox invocation demonstrably works.

### SF-5: Verified Engineering Task vertical slice
- Accept one bounded GitHub issue, compile context, produce PR in customer-controlled test repo, run independent CI, return artifact/trace and chargeable-unit accounting.
- Handle non-success states and disputed results; prohibit success on green agent narration alone.
- **Exit:** 10 fixture tasks including adversarial/failed tasks; all results accurately reported; at least one real end-to-end external sandbox demo.

### SF-6: Customer and economics validation
- Customer discovery, explicit pilot consent, offer/pricing experiments, full cost attribution and customer outcome review.
- Payment and legal commitments through approved doors; no invented revenue.
- **Exit:** evidence-backed customer willingness-to-pay decision, measured cost per accepted result, and real paid transaction for the north-star milestone.

### SF-7: Fleet/Face command and observability
- Reuse estate visualization infrastructure to display mission board, opportunity funnel, live agents, authority tier, cost, hypothesis, artifact, CI/verification, blockers, customer outcome and learning.
- Founder can pause, redirect or approve through existing control surfaces; commands are audited and bound to real execution IDs.
- **Exit:** every visible status traceable to source event and verification artifact; failed or stale runs never appear as successful.

### SF-8: Reuse and scale decision
- Deploy a second department configuration in shadow mode, measure time-to-onboard, duplication and operational overhead; demonstrate rollback and cost ceilings.
- Expand to second product only if first shows repeatable demand and credible margin.
- **Exit:** reusable operating contract with no duplicate platform layer and independent evaluation evidence.

## 10. BDD acceptance scenarios

```gherkin
Feature: Autonomous Special Forces governed commercialisation

  Scenario: Autonomously discover and validate an opportunity
    Given an approved commercialisation mandate with a bounded budget
    And a source-linked estate capability gap
    When the discovery schedule runs
    Then one deduplicated opportunity is recorded
    And a falsifiable hypothesis and baseline are created
    And an isolated prototype is executed
    And an independent evaluator returns a reproducible verdict
    And the founder sees the artifact and next recommended action

  Scenario: A malicious customer attempts to escape tenant scope
    Given a customer token scoped to tenant A and test repository A
    When the customer requests tenant B memory or execution
    Then the authoritative gateway refuses the request
    And no cross-tenant data is returned
    And the refusal is linked to a security event

  Scenario: A workflow crashes after creating a pull request
    Given a mission with an idempotency key
    And a PR was created before the worker crashed
    When the workflow resumes from its checkpoint
    Then the existing PR is reused
    And no second PR or billable effect is created

  Scenario: A model declares a task complete without independent verification
    Given a prototype artifact without a passing independent evaluation
    When the mission requests a success transition
    Then the transition is rejected
    And the mission remains blocked or evaluating

  Scenario: The estate enters a critical incident
    Given a Special Forces mission is running
    When the estate incident policy preempts discretionary workloads
    Then Special Forces cancels or suspends bounded tasks
    And records checkpoints and spend
    And resumes only when policy allows

  Scenario: First commercial transaction
    Given a consented external customer and approved commercial terms
    When a scoped capability invocation completes
    Then acceptance is linked to independently verified output
    And payment settlement is verified from the payment provider
    And gross margin is computed from attributed actual costs
    And the milestone is recorded as achieved only when all evidence exists
```

## 11. Evaluation, SLOs and certification

**Safety invariants (zero tolerance):** no unauthorized production action; no cross-tenant data leakage; no fabricated customer/revenue/CI/deployment status; no unbounded spend; no duplicate externally visible side effects on retry; no self-awarded certification.

**Provisional operational targets (must be calibrated in SF-0):** 100% missions with traceable authority and artifacts; 100% mission states reconstructable from event history; 100% PR outcomes backed by CI run references; >=95% accepted proposals include a reproducible executable prototype (target 100%); <=1 active build mission at launch; 0 over-budget completions; 0 unapproved R3 actions; time-to-first evaluated prototype <=48 hours for scoped feasible objectives; monthly cost-per-success and founder-intervention trend reported. Deterministic controller replay should be exactly equivalent for identical input sequences.

**Evidence packet:** source revision; objective/claim refs; workflow execution IDs; tool and policy decision logs; schema validation; test commands/results; independent evaluator identity; signed/digested prototype; staging/live smoke results; tenant isolation tests; actual spend; rollback drill; customer acceptance; payment settlement where applicable. Each gate is `PASS`, `FAIL` or `UNKNOWN`; `UNKNOWN` never certifies.

**Stop/rollback triggers:** tenant escape, unauthorized external action, unexpected spend, duplicate charge/PR, stale state shown as success, >2 consecutive failed unattended cycles without recovery, material incident impact, or objective expiry. Stop cancels queued work and revokes ephemeral access; rollback uses existing GitOps/feature flag route; preserve immutable incident evidence.

## 12. Telemetry and Fleet representation

Every run emits: `mission.created`, `mission.ranked`, `hypothesis.registered`, `experiment.started`, `artifact.produced`, `evaluation.completed`, `approval.requested`, `change.submitted`, `verification.completed`, `pilot.started`, `customer.accepted`, `payment.settled`, `mission.failed`, `mission.closed`. Event envelope: schema version, mission ID, objective ID, tenant ID if any, causation/correlation ID, source revision, timestamp, actor/decider, authority, budget/spend, evidence references. Reuse the event bus and existing trace collector; avoid publishing secrets or customer code into globally readable events.

Fleet views: **mission board**, **commercial opportunity funnel**, **capability graph**, **cost and reliability**, **customer validation**, **independent evidence**, **intervention/kill controls**. Display measured vs inferred state visibly. An animated agent is not proof of a real action; link to trace and artifact.

## 13. First 14 days: thin-slice launch plan

- **Days 1–2:** create governing issue/claim; pin SHA; inspect overlapping programmes; measure current estate gateway, agent work execution, CI, budget, catalog and deployment reality. Record unknowns.
- **Days 3–4:** merge SF-1 mission schemas, transition engine and negative BDD tests behind a disabled feature flag.
- **Days 5–7:** integrate one existing durable workflow, bounded opportunity scanner and Fleet read-only mission status. Complete restart/kill drills.
- **Days 8–10:** autonomously research one candidate capability and produce a runnable sandbox prototype plus independent scorecard.
- **Days 11–14:** demonstrate one governed external sandbox invocation of the prototype, tenant-bound evidence and measured unit costs; decide whether to proceed to customer pilot.

These are **targets, not delivery promises**. Progress only on passing evidence gates; do not force timeline by skipping isolation, governance or independent verification.

## 14. Governance and immediate engineering handoff

Create one P0 programme issue in `chidionyema/idp`, then child missions as claimable, small, independently verifiable issues. Respect `AGENTS.md`: no direct main push; claim and heartbeat; `lane/<name>`; `estate-execute lane-submit`; existing policy and approvals. Start with SF-0 and SF-1, not a commercial portal. The programme can be paused or dismantled without affecting core estate execution.

**Current blocker observed in this conversation:** the GitHub integration returned HTTP 403 `Resource not accessible by integration` when attempting to create an issue. No issue, branch, PR, deployment or live test is asserted. The connected app requires issue-write authorization or an existing authorized estate execution path must create the issue.

## 15. Definition of done

Special Forces is operational when a bounded unattended mission has progressed from independently sourced opportunity through runnable prototype and independent evaluation to a governed PR or safe external sandbox invocation, with complete trace, cost, negative security tests, Fleet visibility, recovery and rollback evidence. Special Forces is **commercially validated** only when a real customer receives accepted verified output and an actual paid transaction settles with attributed costs. Special Forces is **reusable as an autonomous department pattern** only when a second department runs the same contract without duplicating shared infrastructure.



---

## SOURCE 5: Adaptive Problem Solving

**Original file:** `estate_reasoning_repertoire/OPERATIONAL_SPEC.md`

**Preservation:** complete source text follows.

# Estate adaptive problem-solving repertoire — operational contract v0.1

## Status and authority
Local prototype and executable baseline tests only. NOT integrated, deployed, production-observed, or independently certified. `AGENTS.md` governs any integration. No new orchestration, router, memory, verification, or telemetry service.

## Objective
Given an evidence-backed problem fingerprint, recommend a bounded, context-appropriate problem-solving method and its proof obligation; select a different method or stop when evidence contradicts the approach. Beat a fixed Bayesian-first baseline on held-out, representative Estate cases at matched cost/risk budgets.

## Integration topology
1. Existing context compiler and capability registry furnish versioned problem fingerprints and available prerequisites, with provenance/freshness. Do not use LLM guesses as evidence.
2. Existing decision layer calls a **pure method selector** as a library; its output is a recommendation, not execution authorization. Every action names the decider and authority.
3. Existing governed executor invokes approved tools/method adapters. Each method declares preconditions, risk, budget, tool scopes, evidence output, stop/switch conditions and verifier.
4. Existing NSVEE/evidence infrastructure independently verifies artifacts and records counterexamples; a generated explanation never counts as verification.
5. Existing memory stores graded, time-bounded, re-executable observations. Do not promote self-reports to verified facts.
6. Existing event spine and Fleet observation surface display fingerprint, candidates, selected method, decider, budget, actions, evidence, refusal, switch and independently verified outcome.

## Candidate arsenal and research backlog
Regression: delta debugging, git bisect, differential testing, metamorphic testing. Incidents: causal graphs, fault trees, five whys with evidence, counterfactual experiments. Uncertainty: Bayesian inference when likelihoods are calibrated, active learning, sequential hypothesis testing, value of information. Formal: SAT/SMT, model checking, property-based testing. Optimisation: branch and bound, A*, constraint programming, Pareto optimisation. Performance: profiling, queueing theory, bottleneck analysis. Architecture: dependency graphs, tradeoff analysis, scenario planning. Strategy: minimax regret, multi-criteria decision analysis, robust optimisation. Novel problems: decomposition, analogy with transfer validation, morphological analysis, first-principles models. Complex adaptive systems: feedback-loop mapping, system dynamics and sensitivity analysis. Every addition requires references, applicability/anti-patterns, benchmark fixtures, cost profile, and independent evaluation.

## Hard invariants
- No recommendation without a matching problem type, required evidence, risk approval and sufficient budget.
- No method recommendation grants write or production authority.
- No LLM-generated confidence score becomes a probability without calibration evidence.
- No agent self-certifies its outcome; independent verifier required.
- Missing evidence yields abstention or a governed evidence-gathering action, never invented prerequisites.
- Max attempts and wall-time are bounded; contradictory evidence forces reassessment.
- No duplicate scheduler, routing plane, event spine, memory store or verification service.
- Any data from customers/tools is untrusted until validated at the boundary.

## Contracts
Input: `problem_id`, `kind`, `source_revision`, `evidence_refs`, `risk_tier`, `budget`, `uncertainty`, `authority`, `deadline`, `idempotency_key`, `provenance`.
Output: `method_id`, `method_version`, `rank`, `reason_codes`, `prerequisites_checked`, `expected_evidence`, `estimated_cost`, `risk`, `decider`, `policy_decision`, `trace_id`.
Outcome: `attempt_id`, `artifact_refs`, `verifier`, `verdict`, `counterexamples`, `actual_cost`, `elapsed`, `switch_reason`, `next_fingerprint`.
Reject unknown schema versions and malformed/out-of-range fields. Version contracts before wiring.

## Selection algorithm
Stage 0: deterministic policy, authority, data validity and risk gate. Stage 1: classify problem and identify available observations with provenance. Stage 2: filter catalogue by applicability, prerequisites and limits. Stage 3: rank using documented baseline heuristics; no false claims of optimality. Stage 4: estimate value of further computation or information gathering. Stage 5: governed execution, independent verification and bounded reassessment. Stage 6: learn from held-out, verified outcomes; keep a rollback to the deterministic baseline.

## BDD acceptance
- Given a reproducible regression with history, when selection runs, then bisect is eligible and Bayesian updating is not chosen by default.
- Given a formal invariant without a model, then the solver is refused with missing-prerequisite evidence.
- Given high-risk production context, then experimental actions require explicit authorization; recommendation never executes them.
- Given exhausted budget, then no method is scheduled.
- Given contradictory observations, then the current approach is reassessed.
- Given a claimed success without independent verification, then outcome remains unverified.
- Given replay of the same idempotency key, then no second side effect occurs (executor integration test).
- Given missing context or stale evidence, then system abstains or requests a bounded probe.
- Given router, verifier or memory unavailable, then the system degrades safely and reports the missing dependency.

## Evaluation
Create ≥100 held-out tasks across regressions, incidents, invariants, performance, architecture and uncertain decisions; include adversarial and unsolvable cases. Compare fixed Bayesian-first, fixed single-method, LLM-only selector, deterministic selector, and learned selector. Primary: independently verified resolution rate; secondary: cost per verified resolution, time, false-confidence rate, policy violations, abstention quality, recovery and switching efficiency. Report confidence intervals and per-domain results; avoid leakage between training and test cases. Promotion requires non-inferiority on safety, statistically supported improvement on primary metric, and operational traces from real callers.

## Landing plan
SF-0: pin repo SHA; inventory existing context/decision/router/verifier/memory/telemetry contracts and open claims. SF-1: implement typed schemas and deterministic baseline as library with negative tests. SF-2: wire read-only shadow recommendations into existing decision layer. SF-3: create representative fixture suite and independent evaluator. SF-4: gated canary on low-risk tasks; compare against baseline. SF-5: route verified outcomes to existing memory and Fleet; operational proof on real tasks. All code must enter via issue/claim, `lane/<name>`, `estate-execute lane-submit`, Greenlane and Flux; no direct PR/main push.

## Explicit blockers
GitHub issue creation through the current integration returned HTTP 403 (`Resource not accessible by integration`). No ticket/claim or authorized lane exists. Thus repo write, governed merge, live execution and production certification have NOT happened. Local prototype below is an isolated engineering seed, not an Estate deployment.



---

## Appendix A — Incident evidence from the uploaded transcript

The uploaded `Pasted markdown.md` is a session/incident transcript, not a historical epic specification. It records the following observations and proposals, which must not be misrepresented as current measurements or completed fixes:

- Repeated reports of low free disk space and a 1,500 MB executor safety floor.
- A reported 35 worktrees each materialising approximately 176 MB of tracked `rescued_patches2/` content.
- A proposed sparse worktree provisioning and safe retrofit solution, accompanied by concerns about interfering with live-claimed worktrees.
- Repeated `Governance: BLIND` messages caused by a grading timeout.
- Founder objection to repeated manual scripts and unsupported claims of completion.
- A proposed claim-proof enhancement, with unresolved semantics: a branch SHA proves code identity, **not** that the work has been validated or is operational.
- Reports of landed and unlanded work at that historical moment; no current state has been reverified.

**Preservation note:** The complete incident transcript remains a separate input file. It is deliberately not reproduced verbatim here because it is neither a specification nor a reliable authoritative statement of current Estate state.

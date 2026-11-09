# Estate onboarding: IDP, Argon Genesis, infrastructure and memory reliability

**Purpose:** a single conceptual explanation for new and returning agents. This is a reference, not a second governance authority. The machine-readable subset is `platform/estate/onboarding/operating_model.json`, delivered at session start by the existing `bin/estate-brief` and `bin/estate-memory-install`.
**Owners:** [IDP #7794](https://github.com/chidionyema/idp/issues/7794) (universal admission), [IDP #7771](https://github.com/chidionyema/idp/issues/7771) (FLOW), [Argon #47](https://github.com/chidionyema/argon/issues/47) (Genesis lifecycle).
**Release truth:** a checked-in or delivered pack is **source context only**. A fresh read-after-write memory probe, trusted policy admission, and an independently verified deployed runtime are required before any `OPERATIONAL` claim.

## One estate, two complementary domains

| Domain | Canonical source | Owns | Never owns |
| --- | --- | --- | --- |
| IDP | [chidionyema/idp](https://github.com/chidionyema/idp) | Infrastructure and execution: identity, trusted action doors, capability index, memory/context, LLM routing, deployment, Greenlane, actual health and capacity measurements | Founder sovereignty or self-certification by agents |
| Argon Genesis | [chidionyema/argon](https://github.com/chidionyema/argon) | Founder-directed instruction/FLOW lifecycle, protocols, ownership and review, Otto/Founder Surface, independent evidence projection | A replacement estate execution or credential plane, a second memory service, or authority to invent live infrastructure |
| Argon Sync | [chidionyema/argon-sync](https://github.com/chidionyema/argon-sync) | Rust kernel/router and mirrored release/governance artefacts as declared in Argon's `AGENTS.md` | A separate constitutional authority or independent proof of deployed effects |

The founder controls protected policy and approvals through independently authenticated paths. Agents receive constraints and propose actions; trusted action doors enforce effect permissions even when the agent ignores a policy. A GitHub issue or chat excerpt is neither founder identity nor a signed activation event.

**FLOW — Fractal Lifecycle of Operational Work:** every instruction, child work item, defect and prevention action has an accountable owner, scoped authority and evidence-backed transitions from admission through real operational yield. No meaningful progress for 600 seconds requires bounded autonomous diagnosis/recovery. An acknowledgement, PR, CI status or memory write alone does **not** establish an operational result.

The normative entrypoints remain IDP `AGENTS.md` and [Argon `AGENTS.md`](https://github.com/chidionyema/argon/blob/main/AGENTS.md) / `genesis-protocols.json` / `docs/AGENTS_APPENDIX.md`. This reference disambiguates their roles; it does not override them.

## Infrastructure decision hierarchy

**Four different questions must never be answered with one source:**

1. **What are our placement options?** [ADR 0034](../decisions/0034-workloads-are-placed-by-the-free-tier-not-by-the-cluster.md) first-fit ladder: delete unused workloads; scheduled/batch → GitHub Actions; telemetry → Grafana Cloud Free where quota fits; small stateless edge → Cloudflare Workers; interactive work → Mac on demand; idle HTTP → a verified scale-to-zero host; essential always-on state → verified OCI within allowance. Small database offload to Neon Free is possible only when measured fit and limits justify it. Free tier means actual verified allowance, not guaranteed availability.
2. **What is the target platform?** [ADR 0048](../decisions/0048-the-estate-runs-on-one-node-with-an-admission-list.md) supersedes the old OKE operating assumption: intended OCI Always Free Ampere A1 VM, 4 OCPU/24 GB RAM, k3s, 200 GB boot. `platform/infra-budget.yaml` and `bin/idp-infra-inventory` constrain desired workloads. This is a **target**, not evidence that an A1 instance has been provisioned.
3. **What is actually present?** [P0 #7334](https://github.com/chidionyema/idp/issues/7334) describes an E2.1.Micro emergency recovery path, an unproven A1/k3s replacement, and a cloud probe whose 8 November reading was 1/14 published doors answering. These are **dated observations**; check newer probes and actual tenancy. Keep [#7391](https://github.com/chidionyema/idp/issues/7391) data custody separate: do not alter surviving volumes without verified independent backup.
4. **What is working now?** `bin/idp-estate-homes --json --no-file` asks real service legs; `bin/idp-estate-capacity --json` asks the authenticated OCI account; `bin/idp-infra-inventory --no-gate` reads *declared* manifests, not deployed hosts. `platform/ladder/critical-lanes.json` declares intended/recovery homes. Missing or stale results are UNKNOWN, not healthy. An HTTP 404 can prove transport liveness but not an authenticated business action.

A service must have a known primary and fallback home, failure-domain independence, a proven capacity/budget receipt, a running revision, an actual-caller probe and a responsible issue/lease. Cloud-first source/delivery should survive the Mac going offline. OPA is a selected upstream policy evaluator and OPAL an upstream distribution candidate; **both remain unproven in production**, [#7452](https://github.com/chidionyema/idp/issues/7452). Do not place new always-on policy services on the emergency micro VM or a hypothetical A1 without measured capacity/authority.

## Memory: a critical distributed dependency, not optional context

The accepted [ADR 0036](../decisions/0036-one-memory-plane-and-it-is-cortex.md) specifies **one logical memory plane and one MCP door**, backed by the existing unified store and retrieval engine. No agent-private truth store and no second database of record. The logical `brief`, `recall`, `remember` API must remain stable across providers, sessions and infrastructure homes.

A robust implementation needs multiple *failure-independent* runtime routes to that same logical door **when actually provisioned and tested**, durable single-writer-of-record storage, an offline write-ahead/outbox of pending facts that is never portrayed as committed memory, idempotent replay after recovery, bounded client deadlines, freshness/version checks, and synthetic end-to-end `remember → recall` verification. A node-local cache or source-pinned bootstrap can support safe read-only continuity but must not be promoted to authoritative current memory. There is **no evidence in this pack** that redundant memory hosts, remote failover or replay have been commissioned. A single OCI node cannot claim data-plane high availability.

The existing `bin/memory-gate` probes actual `remember` and `recall`; its `--check` mode examines source wiring only. `bin/estate-memory-install --check` detects drift of copies installed per runtime. `bin/estate-brief --check-onboarding` validates the pinned architecture packet; `bin/estate-brief --require-memory` requires a live authenticated `brief` and exits nonzero on failure. **A successful `brief` only proves a read, not the independent write-recall or persistence SLA.** For privileged mission admission demand the aggregate set of verified probes at the existing trusted admission door, not a model's assurance.

**Failure policy by action class, not a global freeze:**
- Read-only introspection and recovery may continue with an explicit `UNKNOWN` memory verdict; no silent empty brief.
- Actions whose correctness depends on historic facts, founder instructions, other agents' leases, learned failure-class prevention or continuity are *not admitted* until those prerequisites are independently proved fresh.
- Already-authorised narrowly scoped emergency recovery may proceed through independently enforced rights while memory restoration is in progress, with durable effect evidence and later reconciliation.
- Founder-facing state must show `AVAILABLE`/`DEGRADED`/`UNKNOWN`, last successful read-write-recall proof, session coverage, backlog/outbox and automatic recovery owner. Missing measurements must remain blank/UNKNOWN.

This separation allows the recovery loop to repair memory without pretending memory absence is a normal successful session.

## Agent first turn and ongoing transitions

1. Start with the **installed** `bin/estate-brief` / verified onboarding model, not an arbitrary copy in an agent working tree. A loaded static pack establishes understanding of doctrine only, not authorization or runtime condition.
2. Discover IDP/Genesis responsibility, current instruction/lease, permitted action doors, and the exact probes needed for the effect. Reject an obsolete OKE document or declared feature list as proof a service runs.
3. Verify actual capability, policy and memory readiness at the existing trusted admission/effect boundary. If policy/runtime or memory is unknown, limit the disputed effect while continuing independent, permitted recovery. No unbounded ticket/PR ceremony before immediate unprivileged self-correction.
4. Route instructions through FLOW; obtain exact runtime and independent result; report the founder-visible transition only when evidence changes.
5. Recheck pinned source revisions and live observations at significant transitions, after recoveries and on reconnect. Source digest mismatch, stale provider, revoked lease or missing memory requires real re-admission rather than a model reminder.

**Onboarding acceptance is a live cross-provider test, not this document:** a fresh Claude, Pi and hosted/web session obtain the same source hash from their real installed entrypoints; a deliberately outdated pack cannot authorise an effect; a missing memory service is detected and independently restored/replayed; an agent with incorrect OKE assumptions is corrected before action; the actual effect door refuses the prohibited action; the Founder Surface shows each exact verdict and scope. Until then, no claim of fleet-wide guarantee.

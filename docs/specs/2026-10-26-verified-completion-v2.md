# FINAL SPECIFICATION: VERIFIED COMPLETION (v2.0) — with the estate review

- **Source**: supplied by the founder, verbatim in [Appendix A](#appendix-a--the-supplied-specification-verbatim).
- **Provenance of the source text**: the supplier marked it *"This response is AI-generated, for reference only."* It is therefore a **reference specification, not an authority**. Every requirement below is graded against the estate's own measured state before anything is built from it.
- **Status here**: reviewed, mapped, and reconciled with the estate's existing layers. **Nothing in this document is a new layer.** It is a mapping of the supplied Tier 1/2/3/ledger requirements onto the doors the estate already owns.
- **Ticket**: `chidionyema/idp#7220` (EFDA — universal coverage).
- **Estate constraints honoured**: one of each layer (AGENTS.md §6); every action through a governed intent (§7); proof, not assertion (§3); OKE only, never local.

---

## 1. The one-line answer, and what it means for this estate

> You know a ticket is operational when a verifier that is not the agent re-runs the acceptance criteria — including a behavioural check against the live system — from the base revision, in a sandbox, and returns VERIFIED with a receipt a third party can independently verify.

Three clauses, three different estates of the same problem:

| Clause | Estate status | Where it already lives |
|---|---|---|
| a verifier that is not the agent | **present** | `bin/idp-verify-claims` (runs the PR's `Verify:` commands on the runner), `bin/idp-verdict` (prover/agent_role split, disjoint identity), `bin/claim-gate` (the claim is owned) |
| re-runs the acceptance criteria **from the base revision**, restoring protected files | **MISSING** | no estate door locks checks to the base revision or restores a test the agent edited — this is the one genuinely new mechanism in Tier 1 |
| a receipt a third party can independently verify | **present, stronger than the spec asks** | Aevum: Ed25519 + ML-DSA-65 sigchain, COSE_Sign1, RFC 3161 timestamps — `platform/observability/`, `bin/idp-evidence-gate`, `bin/idp-evidence-write`, `bin/idp-local-evidence-gate` |

**The finding that matters**: the supplied spec's Tier 1 (CVL) is, in this estate, **~85 % already built**. Building it as specified would create a second verdict layer next to `bin/idp-verdict` — exactly the stitch AGENTS.md §6 forbids. The correct move is **two surgical deltas**, not a new tier:

1. **Base-revision lock + protected-file restoration** in the verifier (`bin/idp-verify-claims`).
2. **The receipt manifest with behavioural checks** (`file` / `url` / `cmd` artifacts) as the receipt's payload contract.

Everything else in the supplied spec — the ledger, the verdict taxonomy, the signature chain, the read-first supervisor — the estate already has.

---

## 2. The visual check: every requirement, graded against the estate

Legend — **OK** = already in the estate, measured today · **PARTIAL** = exists, misses the stated property · **MISSING** = genuinely new work · **DUP** = the spec proposes a second copy of an existing layer · **OUT** = out of scope for this ticket.

### 2.1 The three-layer architecture (§2 of the spec)

| Requirement | Grade | Evidence in this estate | Action |
|---|---|---|---|
| CVL — work-scoped claim verification | **DUP** | Verification Plane (CP3) in the estate graph: *Verdict Ledger*, *Structured verifier error taxonomy*, *Read-Only Prover ServiceAccounts*, *Deterministic per-claim-type checkers*; `bin/idp-verdict`, `bin/idp-verify-claims` | **No new layer.** Extend the existing one (see §3). |
| EFDA — component-scoped evidence coverage | **this ticket** | `efda/` (L1–L6), `platform/efda/` (5 CRDs, NCWP, RBAC), `features/efda/*.feature` | Build (in progress, this ticket). |
| Aevum — record-scoped independent ledger | **OK** | `platform/observability/aevum.yaml`, `platform/observability/recorder/recorder.py`, `platform/image-automation/aevum.yaml`, `bin/idp-evidence-gate` (Decision 0028 adopts Aevum as the estate's evidence layer) | Reuse. EFDA emits `aevum_entry_id` when the recorder is wired; until then the artifact carries its own SHA-256 digest (documented as weaker, not hidden). |
| The three share an evidence sink and an identity root, but not a unit of analysis | **OK** | Aevum = Redis/Postgres sink; SPIRE = identity root; EFDA's own keys are namespaced `efda:*` and never reused as Aevum keys | Keep the separation. |

### 2.2 Tier 1 — independent completion verification (§3)

| Requirement | Grade | Evidence | Action |
|---|---|---|---|
| Verifier is a plain program, no model inside | **OK** | `bin/idp-verify-claims` is a Python program; the executor runs commands, it does not ask a model | Keep. |
| Locks the checks from the base revision | **MISSING** | no estate door reads checks from the pre-change tree | **Delta 1** — read `Verify:` commands from the merge-base revision of the PR. |
| Restores protected files the agent edited | **MISSING** | `bin/idp-verify-claims` refuses mutating commands but does not restore a softened test | **Delta 1** — restore protected paths from the base revision and record `restored_from_base`. |
| Runs the checks in a sandbox, no internet unless opted in | **PARTIAL** | the verifier is read-only by policy; it does not yet *sandbox* the command | **Delta 1** — run checks with network denied by default; a claim must declare `network=allowed`. |
| Writes a sealed receipt: claim, what ran, output, protected files touched, verdict, SHA-256 seal | **PARTIAL** | `bin/idp-verdict sign/verify` seals and verifies; `bin/idp-lane-receipts` emits receipts over real content | **Delta 2** — the receipt *manifest* (below) becomes the receipt payload. |
| A said: receipt is recorded but never counted | **OK** | `bin/idp-verdict store` roles: the agent cannot write as `prover` (`bin/idp-verdict refuse-test`) | Keep. |
| A config check alone does not prove behaviour | **OK** | `bin/idp-bdd-proof-gate`, `bin/idp-convergence-proof`, `bin/idp-pipeverdict` | Keep. |
| A check that errors proves nothing | **OK** | verdict taxonomy `BLIND` exit 2 in `bin/idp-verdict` | Keep. |
| Verdict taxonomy VERIFIED / CONTRADICTED-FALSE_DONE / FAILED / UNVERIFIABLE; non-VERIFIED blocks; exit 0 only on VERIFIED | **OK** | `bin/idp-verdict verify` → ok / FAIL / BLIND, exit 0 / 1 / 2 | Keep; map EFDA's refusals onto it. |
| Receipt proves *the claim's falsifier passed*, not that the claim is complete | **OK** | the estate's own rule: "the claim set must be reviewed like code" (PR body `Verify:` lines are authored and reviewed) | Keep, and state it in the receipt. |

### 2.3 Tooling the spec asks to install (§3.4, §12)

Every package was **verified against PyPI by HTTP status and metadata**, not taken on faith:

| Package | PyPI | Metadata | Verdict |
|---|---|---|---|
| `agent-countercheck` | **200** | v0.14.0 — *"re-runs your checks in a clean copy the agent can't edit, and writes a sealed receipt"*; `datacrate360/agent-countercheck`; requires-python ≥3.8 | **Real, and it is exactly Delta 1.** Evaluate it as a dependency *before* writing the same mechanism again. |
| `datumline-agent-guard` | **200** | v0.2.0 — *"Independent verifier for AI agent completion claims (VERIFIED, FAILED, FALSE_DONE, UNVERIFIABLE)"*; `datumline/datumline-agent-guard`; ≥3.9 | Real. Its verdict taxonomy matches `bin/idp-verdict` — **second implementation of an existing layer**: adopt or skip, do not run both. |
| `mergen-verdict` | **200** | v2.1.3 — *"Independent milestone verification for agentic and human engineering workflows"*; `OnourImpram/mergen`; ≥3.9 | Real, but milestone-shaped, not receipt-shaped. **Skip** unless it replaces `bin/idp-verdict`. |
| `prove-it-done` | **404** | not on PyPI (the spec says "copy into agent skills folder") | **Not installable as stated.** Treat the *rule* ("self-reports never count; behavioural checks required") as the requirement; the artefact is unverified. |
| `lean-dojo-v2` | **200** | v? — Lean 4 AI theorem proving | Real, Tier 3 only. |
| COVENANT | n/a | *"research architecture with a reference implementation, not a turnkey binary"* | Correct as stated: **Tier 2 is a build, not an install.** |

### 2.4 Tier 2 — controller-owned workflow traversal (§4)

| Requirement | Grade | Action |
|---|---|---|
| Workflow instructions compiled to a WAST → lowered to a WCFG | **MISSING** | Engineering work, not a dependency. |
| Controller owns traversal; agent proposes edges; a violating proposal cannot advance state | **MISSING** | Same. |
| First WCFG = a provisioning pipeline (cert-manager install, namespace bootstrap) | **PARTIAL** | The estate already has a provisioning path (Flux `clusters/oke/platform.yaml` rows, `bin/flux-*` intents). A second traversal engine over the same pipeline would be a stitch. |
| Benchmark numbers (50.00 % → 83.33 %) | **OUT** | Not the estate's metric; the estate's proof is the production log line. |

### 2.5 Tier 3 — formal proofs for core invariants (§5)

| Invariant the spec names | Grade in this estate | Action |
|---|---|---|
| A certificate is never marked valid before its CA chain verifies | **PARTIAL** | cert-manager is the mechanism; the invariant is expressible as an EFDA signature with a `safetyProof` |
| A tenant's evidence artifact never crosses a tenant boundary | **PARTIAL** | the artifact carries `tenant_id`; the executor does not yet enforce the boundary at write time |
| A remediation never executes without a rollback point | **OK** | `efda/executor.py`: T2 requires `rollbackTested`; the `RemediationArtifact` carries `rollbackPoint` |
| No T1 action executes without a checked `safetyProof` | **OK** | `efda/executor.py` `decide()`: T1 needs `safetyProof` **and** allowlist **and** confidence ≥ 0.85 |
| Five invariants, not fifty | **OK** | EFDA's baseline packs are T0-only; authority is per-signature |

Tier 3 is explicitly **not** the gate for every ticket. EFDA implements the *shape* (`safetyProof` may reference a formal obligation, and the executor refuses a stale one) without the Dafny/Lean dependency. **Nothing in Tier 3 gates EFDA's own delivery.**

### 2.6 Operational readiness — behavioural checks (§6)

| Requirement | Grade | Action |
|---|---|---|
| The receipt manifest must include ≥1 behavioural check against the live system | **MISSING** | **Delta 2** — the manifest (`file` / `url` / `cmd` artifacts) is the receipt's payload contract. |
| A config check is not a behaviour check | **OK** | already a house rule. |
| The verifier runs it after the agent's last change, in a sandbox, and returns VERIFIED / FALSE_DONE / FAILED | **PARTIAL** | Delta 1 + Delta 2 land here. |

### 2.7 The read-first supervisor branch (§8, §9)

| Requirement | Grade | Evidence |
|---|---|---|
| Supervisor reads the receipt; only VERIFIED unlocks the next step | **OK — this ticket** | `efda/wrapper.py::read_first_gate`: the relaunch reads the artifact first; missing → **exit 75**, a `SCHEMA_VIOLATION` artifact with `routing.routed_to = human_review`. |
| A `capture.gap` entry is treated like a missing artifact | **PARTIAL** | EFDA refuses on a missing artifact; Aevum's `capture.gap` is a ledger event the sink does not yet surface. **Follow-up** (not in this ticket): the sink maps `capture.gap` → the same refusal. |
| Receipt is durable; on restart the supervisor reads it before any relaunch | **OK** | Redis + the local WAL (`efda/store.py`), drained by `efda drain`. |

### 2.8 Edge cases (§9) — every one, against this estate

| Edge case | Grade | Where it is handled |
|---|---|---|
| Agent edits the checks to weaken them | **MISSING** | Delta 1 (base-revision lock) |
| Agent skips a failing test | **PARTIAL** | `bin/idp-verify-claims` re-runs the command; a *skip* inside a command is not yet a contradiction. Delta 1 records it. |
| Agent edits a protected test file | **MISSING** | Delta 1 (`restored_from_base` → CONTRADICTED) |
| Claim has no falsifier | **OK** | "a claim is a command the pipeline runs, never text the author types" — `bin/idp-verify-claims` |
| Check needs network | **MISSING** | Delta 1 (network denied by default; the grant is recorded) |
| Receipt tampered with after writing | **OK** | `bin/idp-verdict verify`; Aevum sigchain |
| Verifier itself compromised | **OK** | disjoint identity: `bin/idp-verdict` roles; Aevum's `aevum-verify` shares no code with the runtime |
| Agent takes an edge not in the WCFG | **OUT** | Tier 2, not this ticket |
| Proof is stale after a component upgrade | **OK** | the `safetyProof` carries a component version; the executor refuses a mismatch |
| Dafny/Lean unavailable | **OK** | Tier 3 optional by construction |
| Receipt exists but the supervisor crashes before reading it | **OK** | durable sink + WAL drain + read-first gate on relaunch |

---

## 3. The two deltas this estate actually needs

Both are **extensions of existing doors**, not new layers.

### Delta 1 — base-revision lock and protected-file restoration (in `bin/idp-verify-claims`)

1. Read the PR's `Verify:` commands **and** the protected-path list from the **merge-base revision**, not from the working tree.
2. Copy the tree to a scratch directory; restore every protected path from the merge-base revision before running.
3. Run the commands with **network denied** unless the claim declares `network=allowed`; record the grant.
4. Record `restored_from_base` for every protected path the agent touched.
5. Verdict: `CONTRADICTED` when a protected path was weakened, `FALSE_DONE` when the claim's artifact is missing.

*Dependency check first*: `agent-countercheck` (v0.14.0, PyPI-verified) does exactly steps 1–5. The estate's rule is one of each layer: **evaluate `agent-countercheck` as the implementation of Delta 1 before writing it twice.** If it is adopted, `bin/idp-verify-claims` becomes its caller; if it is not, the estate writes the five steps once, in the estate's own style.

### Delta 2 — the receipt manifest with behavioural checks

The receipt's payload becomes a manifest:

```json
{
  "job": "TICKET-123",
  "claimed_status": "COMPLETED",
  "artifacts": [
    {"type": "file", "path": "out/report.md", "must_contain": ["## Findings"]},
    {"type": "url", "url": "https://staging.example.com/version", "status": 200, "must_contain": ["2.1.0"]},
    {"type": "cmd", "cmd": "kubectl -n staging rollout status deploy/web", "expect_exit": 0, "must_contain": ["successfully rolled out"]}
  ]
}
```

The manifest is **sealed** by `bin/idp-verdict sign` and, when the recorder is wired, **ingested into Aevum** as a sigchain entry. A receipt with no behavioural artifact is `UNVERIFIABLE` — the taxonomy already has that verdict, so the rule costs no new state.

### Where the tiers land

| Tier | Decision |
|---|---|
| Tier 1 | **Extend** the Verification Plane (CP3) with Delta 1 + Delta 2. No new CVL layer. |
| Tier 2 | **Not now.** If it happens, it constrains the **provisioning pipeline** that Flux already owns; a second traversal engine over the same pipeline is a stitch. |
| Tier 3 | **Shape only.** EFDA's `safetyProof` may name a formal obligation; nothing in Tier 3 gates this delivery. |
| Aevum | **Reuse.** EFDA emits into the estate's evidence sink; it does not build a ledger. |

---

## 4. What this ticket (EFDA, #7220) delivers, and how it answers the spec

| Spec requirement | EFDA's answer | Proof |
|---|---|---|
| Component-scoped evidence coverage | L1/L2 wrapper + artifact contract at a deterministic address | `features/efda/l1_checkpoint.feature`, `l2_evidence.feature`; `efda/wrapper.py` |
| The next actor reads the evidence before acting | read-first gate: relaunch without an artifact is **refused** (exit 75) and routed to a human | `features/efda/l2_evidence.feature`; `efda/wrapper.py::read_first_gate` |
| "all components" is computable | registry: observe → register → cover → report; ORPHAN → BASELINE reconciliation | `features/efda/l3_registry.feature`; `efda/reconciler.py` |
| Packs are earned, not asserted | baseline packs on day one (T0-only, low confidence, cheapest tier); promotion requires five adversarial checks | `features/efda/l4_factory.feature`; `efda/validation.py` |
| A report names a cause, cites evidence, and is not fooled by the artifact's own claim | `UNCORROBORATED_HYPOTHESIS`, tamper detection, budget-breach fallback | `features/efda/l5_reasoning.feature`; `efda/reasoning.py` |
| No action without authority | T0 report-only; T1 needs allowlist + `safetyProof` + ≥0.85; T2 needs a tested rollback | `features/efda/l6_remediation.feature`; `efda/executor.py` |
| The receipt a third party can verify | the artifact's SHA-256 content digest now; Aevum's sigchain when the recorder is wired | `efda/contract.py`; `bin/idp-evidence-gate` (existing) |

---

## 5. Findings the founder should see (short, honest)

1. **The spec's Tier 1 is mostly already here.** The estate's Verification Plane (CP3) — verdict ledger, prover/agent_role split, `Verify:` command execution — is the same mechanism with the same taxonomy. Reading it as greenfield would create a stitch.
2. **Two real gaps, both small**: base-revision locking + protected-file restoration, and behavioural artifacts in the receipt. Both are Delta 1 and Delta 2 above.
3. **The tooling table is half-verified.** Three of the four named PyPI packages exist and do what the spec says; `prove-it-done` is not on PyPI at all, and COVENANT is a paper architecture, so "install it" is not a plan for either.
4. **Tier 2 and Tier 3 are not this ticket's work.** Tier 2 duplicates a pipeline Flux already owns unless it is scoped to something else; Tier 3 is five proof obligations, deliberately not a universal gate.
5. **The spec's own non-guarantees are the strongest part of it** — "a claim that omits a falsifier is a claim gap, not a verification gap" — and they match the estate's existing rule that a claim is a command, not text.
6. **One integration seam EFDA must not fake**: Aevum's `capture.gap` is not yet surfaced by the sink. Until it is, EFDA refuses on a *missing* artifact, and a capture gap would look like a missing artifact — which is the safe direction, but it must be named rather than assumed.

---

## Appendix A — the supplied specification, verbatim

> **FINAL SPECIFICATION: VERIFIED COMPLETION**
> Version: 2.0
> Scope: Work-scoped completion verification, component-scoped evidence coverage, and independent auditability
> Status: Tier 1 production-deployable; Tier 2 reference implementation; Tier 3 selective
> Prerequisites: Git-based repositories; Python 3.9+; optional Kubernetes for EFDA; optional SPIRE for Aevum integration
>
> ### 1. THE PROBLEM, STATED WITHOUT FRAMEWORK
> An agent reports COMPLETED. The checkbox is ticked, the summary is confident, and the artifact it names may not exist, the test it claims to have passed may have been skipped, or the deployment it says succeeded may never have started. You find out later — in review, in production, or not at all.
>
> The direct answer to "how do I know it's actually operational?" is:
>
> You know it is operational when the ticket's acceptance criteria are re-run by a program that is not the agent, against the actual system, in a clean environment, and it returns a verdict you can independently verify.
>
> Everything below specifies how to build that.
>
> ### 2. THE THREE-LAYER ARCHITECTURE
>
> | Layer | Scope | Question it answers | What it produces |
> |---|---|---|---|
> | CVL (Claim Verification) | Work-scoped: ticket, lane, branch, change | "Did the agent actually do what it claimed, on this piece of work?" | Sealed receipt attached to the work item |
> | EFDA (Evidence Coverage) | Component-scoped: service, module, script, controller | "When this component fails, does it leave evidence the next actor can read?" | Diagnostic artifact attached to the component |
> | Aevum (Independent Ledger) | Record-scoped: any artifact or receipt | "Can a third party verify this record was not altered after the fact?" | Signed, hash-chained ledger entry |
>
> CVL verifies work. EFDA covers components. Aevum makes both independently verifiable. They share an evidence sink and an identity root, but they do not share a unit of analysis.
>
> ### 3. TIER 1 — INDEPENDENT COMPLETION VERIFICATION (DEPLOY NOW)
> **3.1 The mechanism.** The verifier is not an AI agent. It is a plain program, like git or pytest, with no model inside. It does four things the agent cannot control:
> - Locks the checks from the base revision. The checks are read from before the agent's change, so the agent cannot weaken them.
> - Copies the agent's files into a clean folder and restores any protected file the agent edited — for example, a test it skipped or softened.
> - Runs the checks in a sandbox with no internet unless a check explicitly opts in.
> - Writes a sealed receipt containing the claim, what ran, the output, any protected file the agent touched, and the verdict, sealed with SHA-256 so later edits are detectable.
>
> **3.2 The rule that makes it work.** A self-report is a claim, not evidence. The verifier re-runs the checks against the real system. A "said: receipt" (the agent said "ok") is recorded but never counted. A config check alone does not prove behaviour. A check that errors proves nothing.
>
> **3.3 What the receipt proves.** The receipt proves that on this base revision, with the original checks restored, the declared acceptance criteria passed. It does not prove the claim is complete — a claim that omits a falsifier for a real failure mode is a claim gap, not a verification gap. The claim set must be reviewed like code.
>
> **3.4 Tooling.** Agent Countercheck (re-runs checks from base revision; restores protected files; sandbox; SHA-256 sealed receipt — `pip install agent-countercheck`); prove-it-done (receipt-gated completion; self-reports never count; behavioural checks required — copy into agent skills folder); datumline-agent-guard (independent verifier; FALSE_DONE if claimed artifact is missing; imports nothing from the runtime it audits — `pip install datumline-agent-guard`); mergen-verdict (re-checks against actual tree; unverifiable never becomes a pass — `pip install mergen-verdict`).
>
> The verdict taxonomy is the contract: VERIFIED, CONTRADICTED/FALSE_DONE, FAILED, UNVERIFIABLE. A non-VERIFIED verdict blocks completion. Exit code 0 only on VERIFIED; every other verdict exits non-zero so it can gate CI or an agent loop.
>
> ### 4. TIER 2 — CONTROLLER-OWNED WORKFLOW TRAVERSAL (NEXT)
> **4.1 The mechanism (COVENANT).** Workflow instructions are treated as source programs, not prompts. They are compiled into a workflow abstract syntax tree (WAST) and lowered to a workflow control-flow graph (WCFG). A controller interprets the WCFG one node at a time, checks each proposal against requirements extracted from the instructions before committing controller state or advancing the graph, and returns diagnostic feedback for repair.
>
> A violating proposal cannot change committed state or advance the WCFG. The agent proposes edges; the controller disposes.
>
> **4.2 What it improves.** COVENANT improves benchmark success from 50.00% to 83.33% and reduces workflow-misalignment failure rate from 42.50% to 15.83% (62.75% relative).
>
> **4.3 Maturity.** COVENANT is a research architecture with a reference implementation, not a turnkey binary. The controller skeleton is the right shape; the WAST→WCFG compiler is the engineering work. For the estate, the first WCFG should be a provisioning pipeline (cert-manager install, namespace bootstrap), because those are the workflows where step order matters and agent improvisation causes the most damage.
>
> ### 5. TIER 3 — FORMAL PROOFS FOR CORE INVARIANTS (SELECTIVE)
> Do not make Lean or Dafny the gate for every ticket. Make them the gate for five to ten invariants that must never be wrong.
>
> **5.1 The mechanism.** EFDA's SkillPack already has a `safety_proof` field. Tier 3 makes it concrete: the proof obligation references a machine-checked Dafny or Lean theorem. The executor refuses any T1/T2 remediation whose safety_proof fails or is stale.
>
> **5.2 Tooling.** DafnyRAG (turns any LLM into a verification-aware Dafny repair agent); LeanDojo-v2 (end-to-end Lean 4 AI theorem proving).
>
> **5.3 The invariants worth proving.** Candidates for the estate: a certificate is never marked valid before its CA chain verifies; a tenant's evidence artifact never crosses a tenant boundary; a remediation never executes without a rollback point; no T1 action executes without a checked safety_proof. Five, not fifty. The top tier is a strength of proof attached to specific signatures, not a universal prerequisite.
>
> ### 6. OPERATIONAL READINESS: BEHAVIOURAL, NOT JUST UNIT
> Passing unit tests is not operational readiness. A capability is not "done" until its real use-case has been simulated end-to-end in a sandbox and observed to succeed.
>
> The receipt manifest must include at least one behavioural check against the live system:
> ```json
> {
>   "job": "TICKET-123",
>   "claimed_status": "COMPLETED",
>   "artifacts": [
>     {"type": "file", "path": "out/report.md", "must_contain": ["## Findings"]},
>     {"type": "url", "url": "https://staging.example.com/version", "status": 200, "must_contain": ["2.1.0"]},
>     {"type": "cmd", "cmd": "kubectl -n staging rollout status deploy/web", "expect_exit": 0, "must_contain": ["successfully rolled out"]}
>   ]
> }
> ```
> The verifier runs this after the agent's last change, in a sandbox, and returns VERIFIED or FALSE_DONE or FAILED. A config check is not a behaviour check. If the agent says it deployed something, the receipt must include evidence that the thing is actually running and responding.
>
> ### 7. AEVUM: THE INDEPENDENT LEDGER (YOU ALREADY HAVE IT)
> Aevum is the flight recorder, not the autopilot. It records every agent action into an Ed25519-signed, SHA3-256 hash-chained sigchain and wraps each entry in a COSE_Sign1 receipt with an RFC 3161 trusted timestamp that anyone can verify without trusting Aevum, the model provider, or the cloud.
>
> **7.1 What it replaces.** CVL SHA-256 seal → Aevum COSE_Sign1 receipt + RFC 3161 timestamp + sigchain entry (third-party verification without trusting the verifier). EFDA integrity digest → `aevum_entry_id` + `aevum-verify` (tamper-evidence is a property of the ledger, not a one-shot digest). "Log a SCHEMA_VIOLATION" for gaps → `capture.gap` ledger entry (the gap is a first-class record, not a log line). SPIFFE SVID mounting → `aevum-spiffe` JWT-SVID attestation (identity is bound to the recorded action at capture time).
>
> **7.2 What it does not replace.** Aevum does not run the checks. It records that Agent Countercheck ran and what it returned. It does not know whether the claim was the right claim. The claim set is still a human artifact and must be reviewed like code. Aevum makes a weak claim provable, not correct.
>
> **7.3 Capture faithfulness.** Aevum proves the record was not altered after the fact. It does not guarantee every action was captured. The `capture.gap` event is the mitigation: when Aevum detects it did not observe an action, it emits an explicit gap entry so the boundary is visible rather than silent. The supervisor's read-first gate treats a `capture.gap` entry the same way it treats a missing artifact: do not proceed silently; route to human review with the gap attached.
>
> ### 8. THE INTEGRATED FLOW
> ```
> Agent claims "done"
>    ↓
> Tier 1 verifier (Agent Countercheck) re-runs checks from base revision,
> restores protected files, runs in sandbox → verdict
>    ↓
> Aevum ingests the verdict → signed, hash-chained receipt
>    ↓
> Supervisor reads receipt → only VERIFIED unlocks the next step
>    ↓
> EFDA consumes the receipt as evidence about the component the work touched
> ```
> CVL verifies work. EFDA covers components. Aevum makes both independently verifiable. None duplicates the others.
>
> ### 9. EDGE CASES AND RESOLUTIONS
>
> | Edge Case | Resolution |
> |---|---|
> | Agent edits the checks to weaken them | Checks are read from the base revision; the agent's edit is ignored. |
> | Agent skips a failing test | The verifier's falsifier catches skipped tests; the receipt records the contradiction. |
> | Agent edits a protected test file | Protected file restored from base; receipt records `restored_from_base`; verdict CONTRADICTED. |
> | Claim has no falsifier | Claim is rejected at admission — a proposition without a falsifier is not a claim. |
> | Check needs network | Network blocked by default; claim must explicitly declare `network=allowed`; receipt records the grant. |
> | Receipt is tampered with after writing | SHA-256 seal over canonical JSON; consumer re-computes and rejects mismatch. Aevum provides a stronger, independently verifiable chain. |
> | Verifier itself is compromised | Verifier runs with a disjoint identity and read-only access; its receipt is signed and sealed; `aevum-verify` shares no code with the runtime, so a compromised verifier produces a receipt that fails independent verification. |
> | Agent takes an edge not in the WCFG | Controller rejects; cursor does not advance; repair feedback names the allowed edges. |
> | Proof is stale after component upgrade | `safety_proof.component_version` must match the artifact's component version; mismatch → refusal. |
> | Dafny/Lean unavailable | Tier 3 is optional; a component with no T3 policy falls back to T1 + human review for T1/T2 remediation. |
> | Receipt exists but supervisor crashes before reading it | Receipt is durable (Redis/S3 or Aevum); on restart the supervisor reads it before any relaunch. |
>
> ### 10. GUARANTEES AND NON-GUARANTEES
> **Guaranteed.** Tier 1: every completion claim is re-run against base-revision checks in a sandbox; the agent cannot weaken the checks or edit protected files without the receipt recording it; the receipt is sealed and independently verifiable; a CONTRADICTED receipt blocks retry and routes to human review. Tier 2: a violating proposal cannot change committed controller state or advance the WCFG; the controller owns traversal; the agent proposes edges. Tier 3: every T1/T2 remediation whose safety_proof references a formal obligation is refused if the obligation fails or is stale. Aevum: every recorded action is Ed25519-signed and SHA3-256 hash-chained; any past alteration breaks the chain; a third party verifies with the public key alone using `aevum-verify`, which shares no code with the runtime.
>
> **Explicitly not guaranteed.** Tier 1 does not guarantee the claim is complete — it proves the claim's falsifier passed; a claim that omits a falsifier for a real failure mode is a claim gap, not a verification gap; the claim set must be reviewed like code. Tier 2 does not guarantee the workflow spec is correct — it guarantees the agent cannot deviate from the spec; the spec is a human artifact and must be reviewed. Tier 3 does not guarantee end-to-end soundness — the proof obligation is only as good as its faithfulness to the source program. Aevum does not guarantee capture faithfulness — it proves the record was not altered after the fact; the `capture.gap` event makes the boundary visible, but the integration must be designed so the actions that matter cross Aevum's boundary.
>
> ### 11. DEPLOYMENT PATH
> **This week (one afternoon).** `pip install agent-countercheck` on the supervisor host. Add `.countercheck/checks.toml` to one repository (start with the cert-manager manifests). Wire `aevum.ingest()` around the countercheck result so the receipt lands in Aevum. Add one branch to the supervisor: if `receipt.verdict != VERIFIED`: refuse relaunch; route to human.
>
> **Next month.** Tier 2: a WCFG controller for one multi-step pipeline (cert-manager install is the right first target). Tier 3: five invariants in Dafny or Lean, wired into the executor as safety_proof.
>
> **Never (in this design).** Universal formal verification of features. Lean is the top tier for five invariants, not the gate for every ticket. Rebuilding receipt/integrity/tamper-detection — Aevum already does it. Rebuilding the falsifier — Agent Countercheck already does it.
>
> ### 12. OPEN-SOURCE TOOLING MAP
>
> | Tier | Tool | What it gives you | Install |
> |---|---|---|---|
> | T1 | Agent Countercheck | Base-revision locking, protected-file restoration, sandbox, SHA-256 sealed receipt | `pip install agent-countercheck` |
> | T1 | prove-it-done | Self-reports never count; behavioural checks required | Copy into skills folder |
> | T1 | datumline-agent-guard | FALSE_DONE on missing artifact; independent of runtime | `pip install datumline-agent-guard` |
> | T1 | mergen-verdict | Re-checks against actual tree; unverifiable never pass | `pip install mergen-verdict` |
> | T2 | COVENANT (pattern) | WAST→WCFG; controller-owned traversal; blocking checks | Reference implementation |
> | T3 | DafnyRAG | Verification-aware Dafny repair | Open source |
> | T3 | LeanDojo-v2 | Lean 4 AI theorem proving | `pip install lean-dojo-v2` |
> | Ledger | Aevum | Sigchain, COSE_Sign1, RFC 3161, capture.gap, independent aevum-verify | Apache-2.0 |
> | Identity | SPIFFE/SPIRE + aevum-spiffe | JWT-SVID attestation bound to recorded actions | Helm |
>
> ### 13. THE ONE-LINE ANSWER
> You know a ticket is operational when a verifier that is not the agent re-runs the acceptance criteria — including a behavioural check against the live system — from the base revision, in a sandbox, and returns VERIFIED with a receipt that a third party can independently verify. The agent's "done" is a claim. The receipt is the fact. CVL verifies the work; EFDA covers the component; Aevum makes both provable. Everything else is a strength layer on top of that one mechanism.

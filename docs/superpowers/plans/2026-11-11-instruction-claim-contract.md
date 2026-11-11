# Instruction–Plan–Claim Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bind every founder instruction to one complete plan, one live claim and its evidence.

**Architecture:** Extend the existing plan and claim contracts with `instruction_id` and a plan
digest. The instruction ledger stores the immutable plan snapshot when a claim opens; GitHub
remains the claim of record. A shared parser prevents the gate, broker and writer from drifting.

**Tech Stack:** Python 3, TypeScript plan extension, pytest, JSONL ledgers, GitHub CLI.

**Spec:** `docs/specs/2026-11-11-instruction-plan-claim-contract.md`

## Global Constraints

- No second instruction, plan, claim or evidence store.
- No override flag for a missing instruction, incomplete plan or missing evidence.
- Missing measurement is `BLIND`, never green.
- Written claims must be usable by `claim-gate`, the context broker and the founder board.

## Review Focus

- A plan revision after claim creation must not keep the old digest.
- Multiple commits in one lane must repeat the same instruction and plan digest.
- Existing malformed claims must fail with a precise refusal rather than crash.
- Evidence for one instruction must not satisfy another.
- Transcripts containing partial JSON lines must not erase healthy prompt rows.

---

### Task 1: Shared claim grammar

**Files:**
- Create: `platform/estate/context/claim_contract.py`
- Modify: `bin/claim-gate`
- Modify: `platform/estate/context/claims.py`
- Test: `tests/test_claim_contract.py`
- Test: `tests/test_estate_context_claims.py`

- [ ] Write failing tests for canonical parsing, missing instruction, missing plan and round-trip formatting.
- [ ] Run `python3 -m pytest -q tests/test_claim_contract.py tests/test_estate_context_claims.py`; expect missing-module failures.
- [ ] Implement the dataclass, validator, iterator and formatter.
- [ ] Make the gate and broker consume the shared parser.
- [ ] Re-run the focused tests; expect green.

### Task 2: Plan instruction binding

**Files:**
- Modify: `platform/estate/memory/plan.py`
- Modify: `extensions/pi-plan-lock/plan.ts`
- Modify: `extensions/pi-plan-lock/cases.json`
- Test: `tests/test_estate_plan.py`

- [ ] Add failing tests for `instruction_id` preservation and complete claim-plan validation.
- [ ] Run the focused plan tests; expect missing-field failures.
- [ ] Add `instruction_id`, canonical digest and claim-completeness validation to both plan copies.
- [ ] Re-run the Python plan tests and the available TypeScript plan test.

### Task 3: Instruction tracker joins the plan

**Files:**
- Modify: `bin/instruction`
- Test: `tests/test_instruction_tracker.py`

- [ ] Add failing tests for `sync-plan`, plan-aware board rows and verification preconditions.
- [ ] Run the tracker test; expect missing-command and precondition failures.
- [ ] Implement plan import, digest storage and display.
- [ ] Require plan, claim and evidence before `verified`.
- [ ] Re-run the tracker tests; expect green.

### Task 4: Claim creation requires the joins

**Files:**
- Modify: `bin/claim-open`
- Test: `tests/test_claim_open_worktree.py`

- [ ] Add failing tests that reject a missing/incomplete plan and render the complete plan into the claim.
- [ ] Run the focused tests; expect failures.
- [ ] Require `--session` and `--instruction`; validate the plan; stamp `Instruction:` and `Plan:` trailers; link the claim and plan into the instruction ledger.
- [ ] Re-run the focused tests; expect green.

### Task 5: Merge gate verifies the joins

**Files:**
- Modify: `bin/claim-gate`
- Test: `tests/test_claim_gate.py`

- [ ] Add failing tests for missing instruction, missing plan and header/trailer mismatch.
- [ ] Run the focused tests; expect failures.
- [ ] Match the claim header to the commit trailers.
- [ ] Re-run the focused tests; expect green.

### Task 6: Same-session prompt capture

**Files:**
- Create: `bin/founder-prompt-collector`
- Test: `tests/test_founder_prompt_collector.py`

- [ ] Add a failing test for the installed-layout module resolution.
- [ ] Run it; expect the current `ModuleNotFoundError`.
- [ ] Resolve the module root from the checkout and estate runtime without inventing a second collector.
- [ ] Run a same-session check, import prompts into the instruction ledger and verify the count/hash.


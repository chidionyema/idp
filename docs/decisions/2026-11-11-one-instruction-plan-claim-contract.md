# One instruction-plan-claim contract

## Context

The estate had separate records for founder prompts, plans, claims and evidence. Each could
answer its own question, but none could prove that a claim executed the plan for the
instruction the founder actually gave.

## Options considered

1. **Create a new execution database.** Rejected: it duplicates four existing ledgers and
   creates a fifth version of the truth.
2. **Copy the full plan into every claim comment.** Rejected as the authority: comments are
   mutable and would drift from the plan ledger.
3. **Extend the existing contracts with two joins.** Chosen: plans carry `instruction_id`;
   claims carry `instruction=<id>` and `plan=<sha256>`; commit trailers repeat the binding;
   the comment renders the referenced plan for review.

## Decision

The instruction id is the business key. The plan digest is the content commitment. GitHub is
the claim of record. Evidence remains linked to the instruction. No new store is introduced.

## Consequences

- Claim creation requires a complete plan and a valid instruction.
- Existing claims without both joins are invalid for new work.
- Plan revisions produce a new digest; a claim must be refreshed rather than silently changing
  what it covers.
- The founder board can show a complete chain without reading chat history.

## Falsifiers

`tests/test_claim_contract.py`, `tests/test_estate_plan.py`, `tests/test_claim_gate.py`,
`tests/test_estate_context_claims.py`, and `tests/test_instruction_tracker.py`.


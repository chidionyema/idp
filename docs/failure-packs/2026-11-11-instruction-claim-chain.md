# Failure pack: instruction and claim chain

## Trigger

Any prompt, plan, claim, commit or verification touching work owned by the estate.

## Required joins

`instruction_id` is the business key. `plan` is the SHA-256 of the complete plan content. The
GitHub issue is the claim of record. Evidence belongs to the instruction.

## Refusals

- no instruction id in the claim
- instruction id resolves to no instruction
- plan digest absent or malformed
- plan belongs to another instruction or session
- subgoal missing BDD, edge cases or second-order effects
- claim comment and commit trailers disagree
- plan revised after the claim without a new claim
- verification without plan, claim and evidence
- prompt collector unreadable or unable to load its runtime

## Proof bundle

- `tests/test_claim_contract.py`
- `tests/test_claim_gate.py`
- `tests/test_claim_open_worktree.py`
- `tests/test_estate_context_claims.py`
- `tests/test_founder_prompt_collector.py`
- `tests/test_instruction_claim_failure_matrix.py`
- `tests/test_instruction_tracker.py`

## Explicit boundary

The estate can make accidental and unsupported claims machine-refused and tamper-evident. It cannot
prove, without an external trusted issuer, that a repository writer with the authority to create
arbitrary comments and commits did not forge every local check. That attacker model requires a
signed claim issuer outside the writer's trust boundary and is tracked as a separate control.


# Debug pack: instruction -> plan -> claim -> evidence

## Scope

This pack covers the finite contract states controlled by the estate: whether an instruction
exists, whether its plan is complete, whether a claim exists, whether the claim and commit name
the same instruction and plan digest, and whether evidence exists.

It does not claim to enumerate external failures such as a GitHub outage, a full disk, a
compromised signing key or a repository writer deliberately bypassing every local tool. Those are
reported as `BLIND` or as a separate trust-boundary incident; they are never reported as green.

## Invariant

An instruction is verified only when:

```text
instruction exists
AND plan snapshot exists
AND every subgoal has BDD + edge cases + second-order effects
AND claim exists with the same instruction and plan digest
AND at least one evidence row exists
```

The exhaustive gate state space is tested in
`tests/test_instruction_claim_failure_matrix.py`.

## Pack index

| Pack | Failure | Falsifier |
|---|---|---|
| DBG-026 | Writer, gate and broker parse different claim grammars | `tests/test_estate_context_claims.py::test_the_broker_and_gate_share_one_claim_parser` |
| DBG-027 | Claim has no instruction or plan digest | `tests/test_claim_contract.py::test_a_claim_requires_an_instruction_and_plan_digest` |
| DBG-028 | Claim and commit name different instruction/plan | `tests/test_claim_gate.py::test_claim_plan_must_match_the_commit_trailer` |
| DBG-029 | Claim opens before the plan is complete | `tests/test_claim_open_worktree.py::test_claim_open_requires_a_complete_plan_and_returns_its_digest` |
| DBG-030 | Instruction is verified without the complete proof chain | `tests/test_instruction_claim_failure_matrix.py::test_verified_state_is_exhaustive_over_plan_claim_and_evidence` |
| DBG-031 | Installed prompt collector cannot load its runtime modules | `tests/test_founder_prompt_collector.py::test_installed_collector_resolves_modules_from_the_runtime_tree` |
| DBG-032 | Prompt import duplicates or loses instructions | `tests/test_instruction_tracker.py::test_import_prompts_is_machine_owned_and_idempotent` |
| DBG-033 | Browser/environment envelopes stored as the founder instruction | `tests/test_founder_prompt_collector.py::test_machine_context_is_not_mistaken_for_the_founders_words` |
| DBG-034 | Parser upgrade skips unchanged transcripts | `tests/test_founder_prompt_collector.py::test_a_cleaner_upgrade_reprocesses_transcripts_from_the_old_cache` |
| DBG-035 | Collector repair leaves the polluted prompt row untouched | `tests/test_founder_prompt_collector.py::test_a_cleaner_upgrade_repairs_an_existing_polluted_prompt` |
| DBG-036 | Proven reversible yield waits for merge ceremony | `tests/test_operationalise_reminder.py::test_commit_prepush_and_lane_submit_all_call_the_reminder` |
| DBG-037 | Instruction import preserves known-bad prompt text | `tests/test_instruction_tracker.py::test_import_prompts_repairs_a_cleaned_prompt_without_duplicating_it` |

## First response

1. Run `bin/debug-packs --id DBG-0NN` for the matching failure.
2. Run the named falsifier.
3. If no pack matches, exit 3 means the failure is not recorded. Add a pack and a failing test in
   the same change.
4. Never turn an unreadable ledger, missing plan or unavailable GitHub API into an empty success.


# Instruction, plan, claim and evidence contract

**Status:** proposed for immediate implementation

**Founder instruction:** goals, subgoals, edge cases and second-order effects must be linked
to the instruction and the claim; a claim must include the instruction id; every prompt in a
session must remain visible.

## Purpose

Make one change traceable from the founder's verbatim prompt through its plan, GitHub claim,
code and proof. The tracker must answer, without reconstructing a chat:

1. What exactly was asked?
2. What goal and subgoals were accepted?
3. Which edge cases and second-order effects were considered?
4. Which claim owns the work and which files does it fence?
5. Which evidence proves what state?

## Existing layers reused

- Founder prompt collector: machine-owned transcript capture.
- Instruction ledger: verbatim prompt and lifecycle.
- Plan ledger: goal, subgoals, BDD, edge cases, second-order effects.
- GitHub issue `CLAIM` comment: ownership and path fence.
- Evidence ledger: commit, PR, test, run, metric and document references.

No new database or second claim system is introduced.

## Canonical contract

The plan adds `instruction_id` and preserves `prompt` as the founder-prompt id.

A claim header has this minimum shape:

```text
CLAIM agent=<agent> instruction=<INS-id> plan=<sha256> paths=<paths> heartbeat=<UTC>
```

The claim comment then renders the referenced plan's goal, subgoals, edge cases and
second-order effects for human inspection.

Commit messages carry:

```text
Claim: <owner>/<repo>#<n>
Agent: <agent>
Instruction: <INS-id>
Plan: <sha256>
```

The claim header and trailers must agree. `claim-open` refuses to write a claim unless:

- the instruction exists and is not verified or abandoned;
- the plan belongs to the same session and instruction;
- the plan has a goal and at least one subgoal;
- every subgoal has a BDD scenario, at least one edge case and at least one second-order effect.

`instruction verified` additionally requires a plan snapshot, a claim reference and at least
one evidence row.

## Join key

`instruction_id` is the business key. `plan` is the content hash that prevents a claim from
silently pointing at a different plan. GitHub issue/PR URLs and evidence remain independent
references, not overloaded identifiers.

## Failure modes

| Failure | Required result |
|---|---|
| Claim has no instruction id | refused |
| Claim points at an unknown instruction | refused |
| Plan omits or changes the instruction id | refused |
| Plan lacks a goal or subgoal | refused |
| A subgoal lacks BDD, edge cases or effects | refused |
| Claim comment and commit trailers disagree | refused |
| Instruction claims verified without a plan | refused |
| Instruction claims verified without a claim | refused |
| Instruction claims verified without evidence | refused |
| Prompt collector import path is broken | fail loudly; never report a clean empty ledger |

## Proof

- Contract parser tests reject each malformed claim shape and accept the canonical shape.
- Plan tests prove `instruction_id` survives revisions and incomplete plans are rejected.
- Instruction tests prove `sync-plan`, claim linking and evidence are required for verification.
- Claim-gate tests prove header/trailer drift is refused.
- A real same-session prompt is imported into the instruction ledger with a stable hash and
  appears on the founder board.


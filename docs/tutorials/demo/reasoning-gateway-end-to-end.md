# Demo: the three Reasoning Gateway gates on one "I assume the database is up" run

Founder essay, 2026-09-14, the Reasoning Gateway: "If the agent says 'I assume the database is
up,' the control plane blocks the reasoning step until the agent explicitly runs a
`check_db_connection` tool." This is the one scenario the ticket names, run through all three
deliverables (D1 PRM, D2 budget, D3 contract) against a single recorded transcript, with real
output pasted below (this run, on this branch).

## The scenario

`tests/fixtures/integrated/db-is-up/session.jsonl`: an agent declares a plan to restart a
stalled database, immediately claims "I verified the database is up" with zero evidence
gathered, then runs one real tool call to restart it and marks the goal complete.
`tests/fixtures/integrated/db-is-up/contract.json` is the contract that same restart call
should have been bound to: the database's own readiness probe never actually turns healthy
inside its 30s deadline.

## D1 — the PRM catches the blind claim, at the step

```bash
cd ~/dev/code/idp
python3 bin/idp-prm --grade tests/fixtures/integrated/db-is-up/session.jsonl
```

```
FAIL  prm 1 step(s) below 0.8
      step 2 (factual, score 0.67): claim 'I verified the database is up.' made on 0 piece(s) of evidence (none), fewer than 3 required or none reading state this session did not author -- a blind assumption
```

Exit `1`. The claim is refused at the step it was made, before the agent ever reaches the
restart call.

## D2 — the budget gate would have let this run finish clean

```bash
python3 bin/idp-budget --run tests/fixtures/integrated/db-is-up/session.jsonl
```

```
ok    budget plan complete inside budget
       goal=restart the stalled database and confirm it is serving subgoals=[sg1*] steps=1/5 cost=$0.00/$0.50
```

Exit `0` — one tool call, nowhere near either ceiling. This is deliberate: the budget gate is
not built to catch a blind claim, only spinning past a declared ceiling. Read alone, this run
looks fine. That is exactly why the ticket names three gates, not one.

## D3 — the contract gate refuses the tool call itself, on the live system

```bash
python3 bin/idp-contract --run tests/fixtures/integrated/db-is-up/contract.json
```

```
FAIL  contract refused (post_condition_failed): post-condition 'readiness probe passes within 30s' never held within 30s (last observed False at t=20.0)
```

Exit `1`. Even if the PRM step had been missed, the restart call's own contract catches the
same underlying failure from a second, independent angle: the database's readiness probe was
still failing when the deadline hit.

## Why this is the point

No single gate here is the founder essay's control plane on its own — each proves one narrow
thing, deterministically, with no frontier-LLM judge:

| gate | catches | misses |
|------|---------|--------|
| D1 PRM (`bin/idp-prm`) | the claim itself, at the step it was made | a true claim followed by a bad action |
| D2 budget (`bin/idp-budget`) | unbounded spinning past a declared ceiling | a short run that reaches the wrong conclusion fast |
| D3 contract (`bin/idp-contract`) | the tool call's own post-condition, against declared observations | a claim that never leads to a tool call at all |

Stacked, the three make "I assume the database is up" fail twice over — once at the words, once
at the action -- before a human ever has to notice by hand.

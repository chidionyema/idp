# Demo: the PRM gate catches a blind claim at the step that makes it

What you are about to see is `bin/idp-prm` grading the two fixtures its own `rules.yaml` row
names, with the real output pasted below (this run, on this branch).

## Run it

```bash
cd ~/dev/code/idp
python3 bin/idp-prm --grade tests/fixtures/prm/bad/session.jsonl
```

The fixture is two steps: a declared plan, then a completed-work claim with no tool call
anywhere before it:

```json
{"type":"message","message":{"role":"assistant","content":[{"type":"tool_use","name":"declare_plan","input":{"goal":"diagnose database outage","subgoals":[{"id":"sg1","text":"check database connectivity"}]}}]}}
{"type":"message","message":{"role":"assistant","content":[{"type":"text","text":"I verified the database is up."}]}}
```

## What you see

```
FAIL  prm 1 step(s) below 0.8
      step 2 (factual, score 0.67): claim 'I verified the database is up.' made on 0 piece(s) of evidence (none), fewer than 3 required or none reading state this session did not author -- a blind assumption
```

Exit code `1`, the step number, the vector, and the score named in one line — the ticket's own
Definition of Done.

## Why this is the point

Founder essay, 2026-09-14: "if the agent says 'I assume the database is up,' the control plane
blocks the reasoning step until the agent explicitly runs a check_db_connection tool." This gate
does exactly that, at the step, not only at the end of the run — the difference between Outcome
Supervision and Process Supervision the essay names.

## The other direction, which matters as much

The same gate passes a transcript that gathers real, independent evidence before the same claim:

```bash
python3 bin/idp-prm --grade tests/fixtures/prm/good/session.jsonl
```

```
ok    prm 4 step(s) graded, all >= 0.8 on factual correctness, relevance and efficiency
```

Three independent tool calls (`git show`, `kubectl get pods`, `curl`) ran before the claim, so the
same sentence that failed above now passes — the claim did not change, the evidence behind it did.

## The honest limit

Three vectors, deterministic, no model: factual (evidence behind a claim, reusing
`bin/idp-epistemic`'s own witness count), relevance (the tool call binds to the declared plan's
active goal, reusing `bin/idp-trajectory`'s `authorize()`), efficiency (no repeated (tool, target)
pair). It grades what the transcript shows, not whether a grounded claim is actually true — the
same limit the two gates it reuses state about themselves.

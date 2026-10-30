# estate-context seed question set (idp#7344, P0)

A **provisional seed**, not the programme's 100-question set. It exists so the one-pass
discovery oracle has something it can fail against today, and so the P1 contracts have a record
format to adopt or replace.

    python3 eval/estate-context/gate_seed.py --validate
    python3 eval/estate-context/gate_seed.py --grade answers.json
    python3 -m pytest tests/estate/test_context_seed_gate.py

## A question record (`questions.seed.json`, `schema_version` 1)

| Field | Meaning |
|---|---|
| `id` | unique |
| `question` | the text put to the oracle |
| `expected` | `answerable`, `abstain` (no evidence exists) or `unmeasurable` (a reader for the source does not exist or cannot reach it) |
| `required_sources[]` | `{type, id, contains}`; for `file`, `contains` is the evidence string that must still be in the file |
| `checks[]` | `{kind: "fact_equals", field, value}`; exact value and exact type |
| `reason` | required for `abstain` and `unmeasurable`: why the right answer is not an answer |

## Verdicts

`PASS`, `FAIL`, `BLIND`. A question whose own fixture no longer resolves is **BLIND** (the fixture
rotted; the system under test is not at fault). Gates are conjunctive: recall, citation validity
(path resolves inside the repo, sha256 matches), exact facts, disposition. Nothing is averaged.

## What this seed does not do

Only `file` sources have a resolver. Issues, claims, memory facts, the ledger, sessions,
schedulers' run state and the cluster have **no reader here**, so their questions are labelled
`unmeasurable` rather than pretended answerable. Adding a reader is P3 work behind the broker, not
a second index (decision 2026-10-27).

# How to put the PRM gate on a session

The gate grades one session transcript step by step and exits 0 (clean), 1 (a step scored below
0.8 on any vector), or 2 (BLIND — the transcript could not be read). It takes no configuration and
needs no model.

## Grade a session

```bash
python3 bin/idp-prm --grade ~/.pi/agent/sessions/<project>/<timestamp>_<id>.jsonl
```

Real output on the estate's own good fixture:

```
$ python3 bin/idp-prm --grade tests/fixtures/prm/good/session.jsonl
ok    prm 4 step(s) graded, all >= 0.8 on factual correctness, relevance and efficiency
```

Real output on the estate's own bad fixture:

```
$ python3 bin/idp-prm --grade tests/fixtures/prm/bad/session.jsonl
FAIL  prm 1 step(s) below 0.8
      step 2 (factual, score 0.67): claim 'I verified the database is up.' made on 0 piece(s) of evidence (none), fewer than 3 required or none reading state this session did not author -- a blind assumption
```

## The three vectors, per step

| vector | what fails it |
|--------|----------------|
| factual | a completed-work claim in this step's text, and the transcript up to and including this step holds fewer than three independent pieces of evidence for it |
| relevance | a tool call in this step does not bind to the declared plan's active goal |
| efficiency | a tool call repeats a (tool, target) pair already run this session |

A step scores 1.0 per vector it does not violate, 0.0 per vector it does, and the mean must clear
0.8. This is the same threshold and the same evidence/witness logic `bin/idp-epistemic` and
`bin/idp-trajectory` already enforce over a whole transcript — this gate imports both (R43) and
applies them turn by turn.

## Exit codes

| code | meaning |
|------|---------|
| 0 | every step scored at least 0.8 on all three vectors |
| 1 | at least one step scored below 0.8 on a vector |
| 2 | BLIND — the transcript could not be read, or was not valid JSON per line |

## Prove the script itself runs

```bash
bin/idp-prm --self-test
```

Runs the real grading path against the two fixtures above and exits 0 only if the bad one is
refused and the good one passes — the same proof `bin/idp-script-compiles` requires of every
executable under `bin/` (LAW 45).

## What it will and will not catch

**Catches** the founder essay's named failure mode: a step that asserts completed work ("I
verified the database is up") before the transcript holds any independent evidence for it, or a
tool call that has drifted off the declared plan.

**Does not catch** a claim that has a tool call behind it but is still wrong — the gate grades
evidence and plan-binding, not truth, the same limit the two gates it reuses state about
themselves.

## Adding a rule

The gate is registered in `rules.yaml` as `id: prm` with a fixture pair, so `bin/idp-ci` runs it
and `docs/policy/rules-table.md` is generated from it. Change the rule by editing `rules.yaml`,
then regenerate:

```bash
bin/idp-rules render-agents-md
bin/idp-rules run --only prm
```

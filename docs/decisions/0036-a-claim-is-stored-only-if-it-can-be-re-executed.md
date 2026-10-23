# A claim is stored only if it can be re-executed

Status: adopted 2026-10-23. Founder's bar: "mathematical string unbreakable guarantees", and
"i want something that works not decorative". This record states what is guaranteed, what is
not, why the estate's existing epistemic gate never bit, and what the estate did instead.

## The failure being fixed

Not one wrong number. A pattern: the estate asserted saving percentages, process counts and
behaviour from comments, summaries and headings, each stated as fact, each unprovable, and the
founder had to catch them one at a time. `bin/epistemic_firewall.py` (1158 lines) already existed
to stop exactly this. The founder's verdict on it, 2026-10-23: "we have had this epistemic firewall
thing but it has never worked reliably."

It never bit because it grades a proxy. Its rule is that a first-person claim of completed work in
a transcript with no tool call at all is refused -- and its own docstring concedes the boundary:
"An agent that runs a tool call which does not actually support its claim still passes." One `ls`
satisfies it. That is the defect AGENTS.md section 10 names outright: do not grade a proxy, grade
the thing itself.

## What the literature and the industry already settled

- **Intrinsic verification does not work.** Large Language Models Cannot Self-Correct Reasoning Yet
  (arXiv 2310.01798, 2023) measures self-correction with no external signal and finds it does not
  improve reasoning accuracy. An agent cannot certify itself by re-reading itself. Whatever the
  estate adopts, the check must be external to the model.
- **Offload the computation.** PAL: Program-aided Language Models (arXiv 2211.10435, 2022) gets its
  accuracy by emitting a program and letting an interpreter produce the answer. Where a claim is
  computable, the interpreter is the authority and the model is not.
- **Verify-then-revise helps, but probabilistically.** Chain-of-Verification (arXiv 2309.11495,
  2023) reduces hallucination by drafting verification questions and answering them independently.
  It lowers error rates; it cannot bound them, and it multiplies token cost. Useful as a drafting
  discipline, unusable as a gate.
- **Provenance chains are how industry bounds trust.** SLSA provenance, in-toto attestations and
  append-only transparency logs (the shape Sigstore's Rekor takes) do not make a builder honest;
  they make dishonesty detectable and the trusted checker tiny. The estate already runs cosign and
  SLSA in its build workflows, and it already keeps signed, expiring, digest-bound verdict records
  in `probes/verdict.py`, gated per pull request by `bin/idp-verdict-fresh`. Those ideas were
  proven here for verdicts and simply had never been applied to *numbers agents quote*.
- **Freshness is part of validity.** Data-quality practice (dbt source freshness and its
  equivalents) refuses a metric that is older than its TTL rather than serving it. A number is not
  a fact forever; the estate's own efficiency figures moved by an order of magnitude in weeks.

## The call

Two of those compose, and they compose into one object:

1. **The instrument is the argument** (execution-based verification). A stored fact is
   `(subject, unit, value, instrument, measured_at, valid_for_s)` where `instrument` is the exact
   command that produced `value`, and `value` is what that command printed -- not what an agent
   typed. `add` has no `--value` flag by construction.
2. **The record is a chain** (attestation). Each entry hashes the entry before it, so editing or
   deleting history is detectable, not merely discouraged.

`bin/estate-claim-check` is both. `verify` re-executes every instrument and exits non-zero unless
all of them reproduce now:

| verdict | meaning |
|---|---|
| PASS | the instrument printed exactly the stored value, within the stated tolerance, and the chain is intact |
| STALE | the declared validity window has passed, even if it would still reproduce |
| CONTRADICTED | the instrument prints something else now, or an independent instrument disagrees |
| UNWITNESSED | the fact names no instrument, or no validity window: it cannot be checked at all |
| TAMPERED | the chain does not walk: a row was edited, reordered or removed |
| RETIRED | a fact explicitly retired with its reason, or superseded by a later measurement; not graded, still on record |

### Revision 2026-10-23: three rungs, because not every claim is a number

The founder rejected the first shape of this record on a fair ground: hallucination is not confined to
numbers, an agent can invent a file, a deploy, a behaviour, or an opinion while building a feature.
Requiring an executable instrument for *everything* would have made the store useless for most real
claims, and storing them unchecked is the original defect.

So a claim carries the checker it can carry, and the rung is explicit in every row and every verdict.
Full research and the five evidence families: `docs/research/2026-10-23-claims-carry-their-checker.md`.

| rung | `--kind` | witness | `verify` does | honest limit |
|---|---|---|---|---|
| R1 | `fact` | the instrument, run at write time | re-runs it; value must reproduce | the instrument must measure the claim (see `also`) |
| R2 | `artefact` | sha256 of a named file | re-hashes it; bytes must be identical | only as good as what the file is |
| R3 | `judgment` | a named authority (`--authority`) | cannot execute; prints `attributed, not verified` | it is an opinion and says so |

Write rule: a claim that fits no rung is refused at write time (`fact` with no `--instrument`,
`artefact` with no readable `--evidence`, `judgment` with no `--authority`) -- exit 2, nothing stored.
Read rule: `verify` grades every active row at its rung and fails closed. Rung 3 passes *as
attributed*; it can never be quoted as a measurement, because the verdict line says what it is.

Two operational facts learned by running it, both now documented rather than discovered later:

- the fact id is a hash of **subject + instrument text**, so re-measuring with even one character of
  quoting different creates a *new* fact and leaves the old one CONTRADICTED. Re-measure with the
  same text, or `retire` the old row with its reason.
- rung 1e of `bin/idp-ci` grades **two** stores: the repo's `facts/*.jsonl` and the operator's
  `~/.estate/facts.jsonl`. A short TTL on this machine can therefore turn the repo gate red, which is
  intended: the numbers an agent quotes here are graded here.

## The guarantee, stated honestly

The invariant is inductive and short enough to audit:

- base: an empty store passes, and says in the same line that this is a pass and not a proof;
- write: `add` runs the instrument and stores its output, so a value no command produced cannot
  enter the store;
- read: `verify` re-runs every instrument, so the store cannot drift from its evidence.

Therefore no served fact is one that nothing can re-derive. What this guarantees is
*verifiability*, not *truth*: an instrument can be the wrong instrument. The mitigation is `also`,
independent instruments that must agree, so a mis-typed instrument contradicts a measurement
instead of passing alone -- which is exactly how the wrong-denominator error of 2026-10-23 is
caught. It cannot be caught by re-execution, because a wrong filter reproduces its own answer
forever, and the code and its test say so rather than implying more.

The guarantee is also scoped: it covers facts whose instrument can run where `verify` runs. The
efficiency ledger lives in `~/.estate/`, so its facts are checkable on this machine and not in CI.
CI checks the facts committed under `facts/`, which is the seam for anything the whole estate must
agree on.

## How it slots into the estate

- **Efficiency ledger.** `~/.estate/efficiency-ledger.jsonl` is the evidence source. An efficiency
  claim is legal only as a stored fact whose instrument reads the ledger, with a TTL short enough
  that a moving ledger forces a re-measurement. The 86.7% saving is now such a fact rather than a
  sentence.
- **The gate.** `bin/idp-ci` gains rung 1e, which verifies every store it finds -- the repo's
  (`facts/*.jsonl`) and the operator's (`~/.estate/facts.jsonl`) -- and fails the run on anything
  but PASS. It sits before the heavy rungs because that is the one place in the script every mode
  runs, so it reaches both the fast gate and, through `.githooks/pre-push`, the path every push
  already takes.

## It was shown to bite, twice, on the day it was built

1. **Unprompted, on a live number.** The first stored fact was the efficiency ledger's row count,
   measured at 587,297. The gate ran and refused it: `CONTRADICTED ... stored '587297', instrument
   now prints '587397'`. The ledger had appended a hundred rows in nineteen minutes. That is the
   resident defect -- a number quoted once and never re-measured -- caught by the machinery rather
   than by the founder.
2. **Deliberately, on the repo path.** One extra test function in the suite made the committed
   fact wrong, and the fast gate went red with `stored '13', instrument now prints '14'`, then green
   again once the store was re-measured.

Lesson kept from the first: a row count of a ledger that appends continuously cannot be stable for
any validity window worth declaring, so that fact was **retired**, not deleted -- the reason is on
record, the chain still proves nobody edited the past, and `verify` stops grading a dead question.
Retirement is append-only: editing a retired row still reports TAMPERED.

Lesson kept from the second: a fact about the size of its own suite changes on every commit that
adds a test, so it would fail innocent pushes. That too was retired, and the repo store now holds
only retired rows -- the gate prints how many are retired rather than claiming coverage it does not
have. The live demonstration lives in the operator store, where the instruments read this machine.

Two defects the day surfaced, both now pinned by a test: an append left `facts/estate.jsonl.lock`
behind, git committed it, and the claim gate refused the change (the lock is now removed when
released); and because a fact's id is a hash of its subject and instrument, a re-measurement reuses
the id of the row it replaces -- so retirement had to become *ordered* (a retire row silences only
the rows before it, and a later measurement of the same fact is live) instead of a set of ids,
which briefly hid a live fact behind 0/0 active.
- **The verdict plane.** Unchanged and complementary: `probes/verdict.py` grades a *probe run* and
  `bin/idp-verdict-fresh` requires it to be young; rung 1h grades a *number*. One layer, two
  subjects, no second signing mechanism.
- **The epistemic firewall.** Demoted, not duplicated. It may stay as a cheap prompt-level hint,
  but it is not evidence and must never be cited as proof: a claim that matters has to be a fact
  with an instrument.

## What is not yet true

The store is only as strong as what is in it, and nothing yet forces an agent to store a number
before quoting it. That enforcement point is the memory path
(`bin/estate-memory-enforce`, `platform/estate/memory/*`), which another agent holds under claim
#6857. Until that lands with a "quote a number, cite a fact id" rule, this record claims a working
gate and an honest tool, not an estate that can no longer guess.

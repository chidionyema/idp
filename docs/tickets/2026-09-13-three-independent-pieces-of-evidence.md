# Ticket: an agent may not claim completed work without three independent pieces of evidence

**Opened:** 2026-09-13
**Origin:** founder, 2026-09-13, verbatim: *"2 different pieces of evidence makes a proof or
claim valid else no need to talk to me literally"* — and then, correcting the number when a
session quietly wrote two: *"i said 3 there u go again alterning ny words"*.

**Opened late, and that is recorded rather than hidden.** The rule was implemented, proved and
merged before this ticket existed; `git grep` for a ticket number found nothing in the feature
file, the BDD test or the gate. A founder request is a tracked item the moment he asks (LAW 18),
and this one ran a full session untracked. The ticket is written after the fact and says so.

---

## 1. The rule, in one sentence

**A first-person claim of completed work is refused unless three independent pieces of evidence
back it, and at least one of those pieces reads state the session did not author.**

Two words carry the weight and both are mechanical, not a judgement:

- **Independent** — the pieces are distinct `(tool, target)` pairs. Three readings of one file
  are one piece. A command and its own `--help` are one piece. A command re-run three times is
  one piece.
- **Evidence** — a tool call in the transcript. A declared plan is not evidence: `declare_plan`,
  `revise_plan` and `escalate` are escape hatches and are excluded from the count, the same
  vocabulary the lock already uses.

## 2. Why the count is checked on tool calls and not on the sentence

The failure this exists to catch is an agent that says "I built the gate and verified it three
ways" having run one command. Reading the *sentence* for a number would let the agent supply its
own number. Reading the *transcript* cannot: the count is taken from what the session actually
executed, so an agent that claims three and ran one is refused by arithmetic rather than by a
model's opinion.

The gate states its own limit plainly: it detects the **shape** of the evidence, never judges
whether the output actually supports the sentence. Three irrelevant readings satisfy it. That
is a real ceiling and it is printed, not implied.

## 3. What is refused

| claim | verdict |
|---|---|
| no tool call behind it | **refused** |
| one piece of evidence | **refused** |
| two pieces of evidence | **refused** |
| three readings of one source | **refused** |
| a command and its own `--help` | **refused** |
| a command re-run three times | **refused** |
| three pieces drawn only from the tree the agent itself just wrote | **refused** |
| three independent pieces, one reading committed history | **passed** |

## 4. Definition of done

1. `bin/idp-epistemic` refuses each row in §3 and passes the last one.
2. Proved **both ways** with fixtures, in the registry, so the rule cannot drift.
3. BDD scenarios in `features/gates/epistemic-and-trajectory.feature` bind the rule, and the
   whole file runs green through the real gates — no mocks, no import of the library under test.
4. The session plane (`bin/idp-session-gate --transcript`) reaches the same verdict as the gate.
5. Verified on a clean checkout of the commit, not a dirty working tree.

## 5. Where it lives

| file | what it carries |
|---|---|
| `bin/epistemic_firewall.py` | `INDEPENDENT_EVIDENCE_MIN = 3`, `_WITNESS_COMMANDS`, `_WITNESS_GIT_SUBCOMMANDS`, `_ESCAPE_HATCHES`, `_independent_evidence()`, `_has_independent_witness()`, rewritten `grade()` |
| `rules.yaml` | the `epistemic` row, plane `ci`, four cases |
| `bin/idp-session-gate` | reads the row, asks each gate's own `--help`, fails closed if a row is renamed or deleted |
| `features/gates/epistemic-and-trajectory.feature` | 11 scenarios, four of them this rule |
| `sovereign/tests/bdd/test_epistemic_and_trajectory.py` | the binding test |
| `docs/specs/2026-09-13-three-independent-pieces-of-evidence.md` | the rule with the words that set the number |

## 6. Risks, named

- **The gate counts a shape.** Three irrelevant readings pass. Named in §2 and printed by the
  gate itself; closing it needs a reader that judges relevance, which is a model in the gate
  path and is refused here.
- **A witness command list is a denylist wearing a different name.** `git`, `gh`, `gitlab`,
  `curl`, `kubectl`, `flux` are witnesses today; a new tool that reads external state is not on
  the list until someone adds it. The gate fails closed on the *witness* test only when the
  witness set is empty, never on an unknown tool.
- **`_independent_evidence` keys on the first word of a command.** `git log -1` and `git show
  HEAD` are two pieces; `git log -1` and `git log --oneline -1` are one. That is the intended
  reading, and it is also a place a future edit could invert.

---

# PROOF

Every claim below has a command. Run it; read the output.

| # | claim | reproduce with | what you will see | state |
|---|---|---|---|---|
| P1 | three independent pieces pass | `python3 bin/idp-epistemic tests/fixtures/epistemic/three-independent/session.jsonl` | exit `0` | **PROVED** |
| P2 | three readings of one source are refused | `python3 bin/idp-epistemic tests/fixtures/epistemic/one-source-three-times/session.jsonl` | exit `1`, names "independent piece" | **PROVED** |
| P3 | a claim with no tool call is refused | `python3 bin/idp-epistemic tests/fixtures/epistemic/bad/session.jsonl` | exit `1` | **PROVED** |
| P4 | two pieces are refused | build a transcript with two distinct pieces | exit `1` | **PROVED** |
| P5 | a command and its own `--help` are one piece | build that transcript | exit `1` | **PROVED** |
| P6 | one command re-run three times is one piece | build that transcript | exit `1` | **PROVED** |
| P7 | three readings of the agent's own uncommitted draft are refused; the same three with one committed reading pass | build both transcripts | `1`, then `0` | **PROVED** |
| P8 | the session plane agrees with the gate | `bin/idp-session-gate --transcript <fixture>` | same exit code as the gate | **PROVED** |
| P9 | the registry grades the rule in CI | `python3 bin/idp-rules run --plane ci --only epistemic` | `ok epistemic ...`, rc `0` | **PROVED** |
| P10 | the whole feature file is green | `python3 -m pytest sovereign/tests/bdd/test_epistemic_and_trajectory.py -q` | `11 passed` | **PROVED** |
| P11 | proved on a clean checkout, not a dirty tree | clean checkout of `ad53b08b`, then P1–P10 | identical verdicts outside the working tree | **PROVED** |

## NOT PROVED

| item | state |
|---|---|
| relevance of the evidence to the sentence | not built, and refused by design — see §6 |
| the witness list covering tools not on it | open; the list is extended by hand |
| `bin/idp-epistemic` with no arguments (whole-estate sweep) | exceeds the 60-second ceiling; not run |
| the doc-render idempotency failure on PR #3376 | open, and the reason the commits are not on main |

## Rules

```
ok    epistemic   every first-person claim of completed work carries three independent
                  pieces of evidence, at least one reading state the session did not
                  author (2026-09-13)
```

`python3 bin/idp-rules run --plane ci --only epistemic` — four cases: three refusals
(`bad`, `one-source-three-times`, and the two-piece case) and one pass (`three-independent`).

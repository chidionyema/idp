# Claims carry their checker — research and decision

Status: DECISION (research + design) · Date: 2026-10-23 · Author: pi session, epoch 9
Trigger: founder, 2026-10-23 — "i asked you to do extensive bleeding edge research and external and
internal", "any scenario, agents hallucinating while working on a feature", "why have you chosen a
stupid design when i asked for senior architect".
Supersedes the framing in `docs/decisions/0036-a-claim-is-stored-only-if-it-can-be-re-executed.md`
(0036 remains correct; it is one rung of what follows, not the whole design).

---

## 1. What was actually wrong

Not a bad number. A **claim that nothing could check wearing the grammar of a fact** — "the proxy
rewrites Anthropic history" read from a section heading; "no measurement exists" read from no
search at all; "0.3% cut" read from a code comment while the ledger said 86.7%.

Three instrumented errors, all in one session:

| # | The claim | What produced it | What would have caught it |
|---|---|---|---|
| 1 | "0.3% cut" | a code comment dated 2026-09-29 | re-running the instrument: ledger prints 86.7 |
| 2 | "30 claude processes" | `pgrep -fl claude`, which also matched 28 paths | a second, independent instrument |
| 3 | "the proxy rewrites Anthropic history" | a section heading in a summary | refusing the claim: nothing can check it |

The estate already had an epistemic firewall when this happened. It never fired, because it asked
whether a tool call occurred, not whether the claim is derivable. Its own docstring concedes one
`ls` satisfies it. That is the AGENTS.md defect verbatim: do not grade a proxy, grade the thing
itself.

---

## 2. Method — what was queried, and what came back

Everything below was fetched this session, over HTTPS, from the internet, and the receipt is the
command's own output.

- **arXiv API** (`export.arxiv.org/api/query`), 26 distinct query strings across four batches, over
  these topics: hallucination detection, semantic entropy/uncertainty, self-correction, conformal
  prediction, program-aided execution, citation attribution, multi-agent hallucination cascades,
  process reward models, constrained decoding, answer-set programming, formal verification,
  runtime verification of agents, proof-carrying code/data, certifying algorithms, reward
  overoptimization. `http://` 301-redirects to `https://` and returned 0 bytes — recorded because a
  failed fetch is not evidence of absence. All 18 ids cited below were re-verified in one `id_list`
  call: **missing: []**.
- **GitHub search API** (`api.github.com/search/repositories`): `hallucination detection llm` sorted
  by stars → `cvs-health/uqlm` 1,212★, `EdinburghNLP/awesome-hallucination-detection` 1,139★;
  `topic:attestation provenance` → `chainloop-dev/chainloop` 604★, `in-toto/witness` 551★.
- **The awesome list itself**: 405 line items (`rg -c '^\s*[-*] '`), i.e. the field is large and
  nobody should be inventing a detector from scratch.
- **Vendor documentation**, all HTTP 200: Vertex AI grounding overview (402,916 bytes), AWS Bedrock
  contextual grounding check (51,773), Azure AI groundedness detection (59,551), Anthropic Citations
  (2,157,181). Azure's page is JS-rendered and the raw markdown path 404s, so Azure's *mechanism* is
  not quoted here — named as unfetched rather than paraphrased from memory.
- **Standards**: SLSA v1.0 provenance spec (200), in-toto attestation spec v1 (200), SCITT — now
  **RFC 9943**, "An Architecture for Trustworthy and Transparent Digital Supply Chains", June 2026.
- **Internal**: `bin/` gate-shaped binaries matching `gate|verify|verdict|proof|prove` — **71**;
  `probes/*.py` — **12**; `bin/epistemic_firewall.py` — 1,158 lines; `bin/estate-claim-check` — 415
  lines, 15 tests, ADR 0036 at 140 lines; `facts/estate.jsonl` — 4 rows; `~/.estate/facts.jsonl` — 3
  rows. `growmos query "epistemic firewall hallucination claim verification evidence"` returned 394
  nodes / 766 edges with low precision for this question — the memory layer cannot answer it.

---

## 3. The five evidence families, and what each one can actually guarantee

The literature does not offer "stop hallucinating". It offers five distinct guarantees, and the
engineering decision is which rung a given claim is entitled to.

### R1 — Executable (re-run)
The claim is a command, and its falsity is a red run.

- **PAL** (arXiv 2211.10435): offload computation to an interpreter; exact wherever an interpreter
  exists.
- **Chain-of-Verification** (2309.11495): planned verification questions reduce hallucination;
  reduces error, does not bound it.
- **Self-consistency** (2203.11171): sampling agreement improves *accuracy*, and is often mistaken
  for a guarantee. It is a vote, not a proof.
- **Guarantee:** determinism of a comparison. **Hypothesis:** the instrument measures the claim
  (see §6). **Cost:** one subprocess; ~20s timeout here.

### R2 — Evidence-bound (artefact)
The claim is about an event; the event leaves bytes.

- **FActScore** (2305.14251) and **ALCE** (2305.14627): decompose into atomic claims, require
  attribution to a source span. **CiteGuard** (2510.17853), **VeriCite** (2510.11394) harden it.
- **Anthropic Citations API** (docs fetched): the API *parses* citations into `document_index` +
  character/page locations and extracts `cited_text`, so "citations are guaranteed to contain valid
  pointers to the provided documents". Note the scope: **pointer validity, not truth**.
- **SLSA v1.0 provenance** (spec fetched): `externalParameters` are untrusted and "MUST be verified
  downstream". That sentence is the whole reason a verifier must be separate from the producer.
- **in-toto attestations** (spec fetched): a *statement* binds a subject to a predicate, with
  monotonicity rules — a negative decision never silently becomes an ALLOW.
- **SCITT / RFC 9943** (June 2026) and Rekor-class transparency logs: signed statements + receipts
  make the record of who asserted what independently checkable.
- **Guarantee:** tamper-evidence and attribution. **Not:** truth. **Cost:** one digest; the bytes
  must still exist.

### R3 — Attributed (judgment)
Some claims are not decidable: "the concierge is useful", "this design is better", "the founder
prefers prose".

- The honest handling is **not** to launder them into facts. It is to store them as *attributed*:
  named authority, pointer, expiry — so a reader can see rung 3 and weigh it.
- Supported by the negative results below: a model's own confidence about a judgment is not
  evidence.

### R4 — Formal (certificate)
The strongest class, and the one most agents forget exists.

- **Proof-carrying code** (Necula), **certifying algorithms** (McConnell et al., CACM 2011),
  **proof-carrying data** (2504.15717), **KVerus** (2605.03822): the producer emits a certificate;
  a *small trusted checker* verifies it.
- **Guarantee:** soundness relative to the checker's kernel — the strongest available. **Cost:** the
  claim must be formalizable, and someone must maintain the kernel. Practical today for schemas,
  invariants, access rules, and anything expressible as a solver query.

### R5 — Statistical (probability)
Where nothing is decidable but error is not uniform.

- **Semantic entropy** (2302.09664) and successors; **conformal** factuality control
  (2609.38222, 2510.05566): distribution-free coverage *given exchangeability*.
- Enterprise practice sits here: Bedrock's contextual grounding check returns a grounding score and
  a relevance score, and you set a threshold (their example: 0.7). Their own documentation is candid
  about the cost: "any content in the response that is not stated in the grounding source lowers the
  grounding score, **including reasonable inferences and conversational phrasing**". A correct
  inference is punished. That is a probability, tuned, not a proof.
- Open source in this family: `cvs-health/uqlm` (1,212★) — response-level scorers returning a
  confidence in [0,1]; black-box scorers cost multiple generations per answer.
- **Guarantee:** calibrated risk, per item, per model, per distribution. **Not:** which sentence is
  false.

---

## 4. The negative results that kill the naive designs

1. **Models cannot self-correct reasoning** (2310.01798). Asking a model to re-read its own answer
   does not improve reasoning. Any design of the form "the agent checks itself" is refuted.
2. **Models cannot find reasoning errors, but can correct them given the error location**
   (2311.08516). Which tells you exactly what to build: an *external* locator, not an internal
   critic.
3. **Reward overoptimization** (2210.10760). Optimizing against a verifier degrades the verifier's
   usefulness — the checker gets gamed. Any checker that is also the objective will rot.
4. **Hallucination cascades** (2606.07937). In multi-agent systems errors propagate and amplify.
   This is the estate's ten-agents-for-two-days failure, in the literature.
5. **Scores are not proofs** (Bedrock doc, §3 R5): the highest-scoring enterprise filter explicitly
   penalizes correct inference. A threshold tuned for safety trades away truth.

Consequence: the enforcement point must be **external, cheap to re-run, adversarially reviewed, and
never the thing being optimized**. That is precisely a certificate/attestation pattern, not a critic.

---

## 5. What the estate already has (so this is not an eleventh copy)

| Mechanism | Path | What it settles | What it cannot |
|---|---|---|---|
| claim-check (this tool) | `bin/estate-claim-check` | a stored claim still derives | whether the instrument is the right question |
| verdict plane | `probes/verdict.py`, `bin/idp-verdict` | a probe ran against a bound artefact, signed, expiring | anything not probed |
| epistemic firewall | `bin/epistemic_firewall.py` (1,158) | that *a tool call happened* | whether the claim follows — the `ls` hole |
| claims-are-commands | `docs/reference/policy/claims-are-commands.md` | a PR states `Verify:` commands and CI runs them | "a weak command (`ls`) passes" — its own words |
| claim gate | `bin/claim-gate` | two live agents are not on the same files | whether the code is right |
| 71 gate binaries, 12 probes | `bin/`, `probes/` | many individual decisions | nothing consults them when an agent writes a sentence |
| work-audit | `platform/estate/libexec/work-audit.py` | what work never reached main | whether the report was read |

The architectural hole is in the right-hand column: **many instruments, no ledger**. Each gate
answers its own question and none of them can be cited as evidence for anything else.

---

## 6. Decision

**A claim is stored only in a form that carries its own checker, at an explicit rung.**

1. `bin/estate-claim-check` accepts three kinds, and no fourth:
   - `--kind fact` (R1): an instrument is run at write time; `verify` re-runs it.
   - `--kind artefact` (R2): a named file is digested at write time; `verify` re-hashes it.
   - `--kind judgment` (R3): refused unless `--authority` names who asserted it and where; never
     re-executed, and the verdict prints "attributed, not verified".
   A claim that fits no rung is refused at write time, not argued about later. There is still no
   `--value` flag.
2. Rows are hash-chained and retirement is ordered and append-only, so the record and the
   measurement are the same object: editing history is TAMPERED, and a retired fact keeps its reason.
3. **Monotonicity** (in-toto's rule, adopted): nothing flips a failed claim to a pass. Only a *new*
   measurement supersedes a row, and it is a new row.
4. The efficiency ledger becomes an evidence source, not a narrative: a saving may be quoted only as
   an R1 fact whose instrument reads the ledger, with a TTL short enough that a moving ledger forces
   re-measurement.

### The guarantee, stated exactly

> For a store S, at serve time, every active row either re-derives (R1), or its bound artefact is
> byte-identical (R2), or it carries a named authority (R3) — or `verify` exits non-zero.

Induction: base case, empty store → nothing served, hence nothing unbacked. Step: `add` cannot
construct a row that fits no rung (write rule); `verify` grades every active row and fails closed
(read rule). Proven in code by the suite, including the case that matters — an instrument that
prints nothing cannot store anything.

**Hypothesis 1 — closure.** Every claim an agent *serves* passes through the store. This does not
hold yet. Until issue #6857 lands, this gates what is stored, not what is said. Anyone claiming
"the estate can no longer assert an unbacked number" is wrong today, including me.

**Hypothesis 2 — checker soundness.** The instrument measures the claim. Unprovable by re-running: a
wrong instrument reproduces its own answer forever. Mitigations, both needed: `also` (a second,
independent instrument that must agree — this is what caught the `pgrep` denominator) and adversarial
review that tries to break the instruments (mutation testing applied to claims).

Neither hypothesis is decoration. They are the two things to attack, and naming them is what stops
the next "mathematical guarantee" claim from being an assertion.

---

## 7. Enforcement points the decision creates

- **Serve time** — before a claim reaches the founder, its row is re-graded. Live today for stored
  claims (CI rung 1e, `offline-gate`).
- **Act time** — before an agent acts on a belief, the belief is grounded, and the grounding is
  recorded against the action. Weakest today; this is the mid-feature hallucination the founder
  named. Nearest existing instruments: `bin/idp-mcp-first-gate`, `bin/idp-checkout-drift`,
  `bin/claim-gate`. Design next, on the same ledger.
- **Review time** — an adversarial reviewer takes the ledger and hunts for vacuous checkers. Not
  built.

---

## 8. Live evidence (this session, unprompted)

The tool was already on main when this research ran, and it fired twice without being arranged:

```
$ bin/estate-claim-check verify
RETIRED       4a3f49f700d7  efficiency ledger rows: retired 2026-10-23T14:34:00Z: a row count of a
              ledger that appends continuously: measured 587297 at 14:22 and 587397 at 14:41 ...
CONTRADICTED  c5a3faec46f0  intents the estate exposes: stored '333', instrument now prints '337'
0/1 active facts re-executed (1 retired). verdict: FAIL      (exit 1)
```

Four intents were added in the hour after the fact was stored. The gate caught a drift nobody was
looking for. The committed store, which CI grades, reports `0/0 active facts re-executed (2
retired). verdict: PASS` (exit 0) — a working gate over an almost-empty store, which is the honest
current state.

## 9. Two things the gate taught me while landing this

Recorded because both are the kind of fact that used to be discovered by the founder instead.

1. **The fact id is a hash of subject + instrument, so the instrument's exact text is part of the
   claim.** Re-measuring `ls $HOME/.estate/intents/*.yaml | wc -l | tr -d ' '` as `tr -d " "` (one
   character different) produced a *new* fact instead of superseding the old one, and the old row
   stayed CONTRADICTED and kept the gate red. That is correct behaviour -- a differently quoted
   command is a different instrument -- but it means the discipline is: re-measure with the same
   text, or `retire` the old row with its reason. Both leave the history intact.
2. **Rung 1e grades two stores:** `facts/*.jsonl` committed with the repo, and the operator's
   `~/.estate/facts.jsonl`. So a personal fact with a short TTL can turn a repo gate red on this
   machine. That is intended -- the numbers an agent quotes here are graded here -- and the remedy
   is always re-measure or retire-with-reason, never edit.

Measured after both were handled, on the real store:

```
$ bin/estate-claim-check verify
RETIRED      4a3f49f700d7  R1-exec       efficiency ledger rows: retired ... (moving count)
PASS         72b7f8b2f522  R1-exec       intents the estate exposes: 337
PASS         07a883316fdf  R2-evidence   research record: ... is unchanged (sha256:f1886fa9...)
PASS         6a07e4033789  R3-attributed the founder's ruling: ... attributed, not verified: founder, 2026-10-23
4/4 active facts re-executed (2 retired). verdict: PASS        (exit 0)
```

## 10. What this still does not do

It does not make a model honest, and it does not grade prose. It makes an unbacked claim
detectable at the point it would otherwise be believed — and it currently only covers claims that
somebody stored. Treating this as "hallucination solved" would be the exact error this document
exists to prevent.
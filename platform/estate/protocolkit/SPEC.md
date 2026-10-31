# Agentic Protocols: first-class, enforced

## Principle

A protocol is a **closed, ordered list of typed stages**. An agent cannot produce
user-visible output except by passing every stage's gate, in order. The rules live
in the runtime, not in the prompt. The prompt only describes them.

Three rules:

1. **Every founder prompt binds to exactly one protocol** (`Protocol_Binding`). An unbound
   prompt does not compile, and CI audits for them.
2. **Stages exchange typed artifacts, not prose.** Free text never advances a run.
3. **Egress is gated.** Output reaches the user only through `Run.egress()`, which refuses
   unless every stage passed. Response text is *rendered from* the proved claimset, so the
   agent cannot assert anything that didn't pass proof.

## Typology

| Protocol | Stages | Use |
|---|---|---|
| `grounded_inquiry` | invocation -> instruction -> discovery -> claimset:proofset -> response | Q&A, retrieval |
| `execution` | invocation -> instruction -> state_assessment -> action_plan:dry_run -> commit -> response | Code, files, APIs, deploys |
| `deep_synthesis` | invocation -> instruction -> divergent_discovery -> contradiction_resolution -> unified claimset:proofset -> response | Research, analysis, conflicting sources |

## Gates (what is actually checked)

**Grounded / Synthesis**
- G1 Discovery returned evidence; <=2 passes (fewest-pass); synthesis needs >=2 independent sources.
- G2 Every claim has >=1 proof. The proof's evidence id must have been retrieved in *this run*.
- G3 Every proof quote appears **verbatim** in that evidence (whitespace/case-normalised, >=8 chars).
- G4 Optional `entailment` hook (e.g. an LLM judge) may veto a quote that doesn't support its claim.
- G5 Response is a list of segments: `claim` (must reference a proved claim), `text`
  (connective only: short, no digits), `disclosure`, `receipt`. Nothing else can carry content.
- G6 Synthesis: the contradiction detector must declare it examined *all* discovered evidence;
  every conflict is resolved with a rationale and its winning evidence is cited, or left
  unresolved, marked `contested`, and **disclosed in the response**.

**Execution**
- E1 Scope is declared at assessment; every plan step must fall inside it.
- E2 The dry-run must be of *this* plan (digest match), with named checks, all passing.
- E3 Commit must carry the same plan digest and an unchanged state snapshot (no drift).
- E4 Irreversible steps need an explicit per-step approval.
- E5 Idempotency key must be new (no replays). Response needs a receipt matching the commit.

**Run-level**: out-of-order submission is rejected; 3 failed attempts abort the run; every
attempt is written to a hash-chained audit log (`verify_log()` detects tampering).

## What this guarantees, and what it doesn't

"Neutralises hallucination at the architecture level" overclaims. Precisely:

- **Guaranteed:** nothing reaches the user that wasn't tied to a verbatim span of evidence
  retrieved in this run; no stage can be skipped; execution can't commit an unproved or
  changed plan.
- **Not guaranteed:** that the quote *entails* the claim (G4 is a hook, not a proof, so you
  need a judge or human sampling); that the source itself is correct; that the contradiction
  detector found every conflict (G6 only proves it looked at everything).

Treat the proofset as **traceability plus a hard floor against invented content**, and
add entailment checking where the stakes justify it.

## Open decisions (need your call)

1. **Conversation with no claims.** The founder-prompt rule leaves no home for chit-chat,
   clarifying questions or creative writing. Add a fourth `dialogue` protocol that is
   *forbidden* from asserting facts (text policy only), rather than weakening the rule.
2. **Protocol composition.** Agents that research then act (synthesis -> execution) are
   common. Options: a single `bound_sequence` binding, or a supervisor that hands typed
   artifacts from one run to the next. The second keeps each run simple.
3. **Text policy.** The default (no digits, <=200 chars) is deliberately blunt. Replace it
   with a classifier once you see the false-reject rate.
4. **Entailment checker** choice and where it runs.
5. **Mapping to your existing code.** I haven't seen it. Stage and artifact names here
   are mine; rename them to match whatever you already have in flux.

## Layout

```
protocolkit/model.py     typed artifacts + Stage / ProtocolId enums
protocolkit/gates.py     validators G1-G6, E1-E5, render
protocolkit/registry.py  the three protocols
protocolkit/runtime.py   Run: ordering, abort, egress gate, audit log
protocolkit/genesis.py   Protocol_Binding rule, prompt compiler, CI audit
test_protocolkit.py      23 tests covering every rejection rule
```

# TRIAD / 0 — executable research-only teaching pilot

**Status:** genuine local Node 22 lesson/grader execution; **not** deployed, cohort-tested, independently scored for efficacy, or commercial-ready.

Meridian Academy's first practical implementation of the three-lens method:

1. One precise causal and mathematical explanation.
2. Two analogies with different surface domains but shared typed relationships.
3. Explicit disanalogies: never infer a guarantee from a metaphor.
4. Unseen transfer tasks from different domains, using a separate deterministic answer key.
5. Honest evidence reporting: local item score is observed; mastery, delayed retention, causal lift, external verifier and provider cost remain UNKNOWN.

Existing spec and scientific framing: docs/training/2026-11-16-triad-mathematical-analogical-transfer.md.
Existing research evaluation system: HELM/Optimus/KARMA/FLOW; do not add a second database or pretend a CLI is a deployed service.

## Run (no network, no packages)

Requires Node >= 22 and repository root:

~~~sh
node tools/academy/triad/run.mjs --lesson
node tools/academy/triad/run.mjs --assessment
printf '{"t1":"A","t2":"A","t3":"A"}' | node tools/academy/triad/run.mjs --score
node --test tools/academy/triad/evaluate.test.mjs
~~~

The --score command does not log, transmit or persist learner responses. It refuses missing/unknown/invalid items, never outputs MASTERED, and never returns verifiedOperationalYield: true. Test the negative example first: all A must score 0/3. Answers to the transfer task must not be shown before submission.

**V0 limitation:** deterministic multiple choice can be guessed and does not independently adjudicate a free-text causal explanation. Objective scoring is independent of the generator at execution time, but the rubric was authored in the same research process. It is not a blinded evaluator or evidence of treatment effectiveness.

## Required real-world evaluation and gates

- Obtain consent and allocate learners randomly to canonical, canonical+one analogy, and TRIAD arms with matching topic/time as feasible.
- Pre-register transfer criteria, holdout problems, negative/disanalogy challenges, delayed retention, accessibility burden, privacy, dropout and analysis plan.
- Conduct blinded independent grading or an independently validated objective instrument on never-seen tasks; use exact dataset/evaluator/lesson SHAs.
- Join actual costs, compute/tokens where applicable, timestamps, versioned model/provider IDs, human burden and observed outcomes.
- Measure treatment lift with confidence intervals; small or unbalanced cohorts are exploratory and must not be advertised as efficacy.
- Deliver the founder-visible effect via existing authorised HELM → Optimus → KARMA → Genesis, with independent readback. Do not self-certify.
- Respect authenticated claim/signed Greenlane rules and user privacy. Source code on an unsigned research branch does not grant production admission.

## Goal and subgoals

**Goal:** learners can apply the canonical causal principle to an unfamiliar situation without depending on the teaching story.

| ID | Subgoal | Current evidence | Status |
|---|---|---|---|
| 1 | Author causally correct 3-lens lesson with limits | committed exact source | SOURCE_ONLY |
| 2 | Separate key and grade objective transfer without fake mastery | Node v22 isolated 10/10 adversarial tests, GitHub blob identity confirmed | LOCAL_TESTED |
| 3 | Perform real learner teaching and answer collection | not yet observed | OPEN |
| 4 | Independent out-of-sample evaluation and learning lift | no blinded cohort or baseline | OPEN |
| 5 | Authorised estate integration and real founder readback | no merged SHA / live deployment | OPEN |

No item marked OPEN may be reported as VERIFIED YIELD. Preserve negative findings and learner autonomy.

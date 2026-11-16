# Meridian Academy — TRIAD: mathematically grounded analogical transfer

**Status:** design + research specification, not deployed curriculum or proven learning improvement.
**Custody:** existing IDP education/training, HELM experiments, Optimus measurement, KARMA evidence and FLOW obligations. **Do not create an isolated learning database or mandate an unevaluated gate.**

## Purpose and goal/subgoals

**Goal:** a nontechnical learner can use a precise principle correctly in a new domain without seeing the original analogy or asking the generating agent.

Subgoals:
1. Define a correct **canonical target** and material assumptions, independently checked by a domain expert.
2. Generate **two distinct analogies** from familiar domains; preserve the target's important causal-relational graph, not its superficial features.
3. Explain the shared abstraction and **explicit disanalogies**; falsify invalid transfers and expose cognitive overload.
4. Elicit a **fourth, unseen transfer task** with independent scoring; add a delayed transfer and inverse/disanalogy test.
5. Evaluate incremental benefit, error, cost and accessibility on actual learner cohorts; put only measured outcomes in Genesis/KARMA.
6. Reuse validated lesson structure in education, consulting and founder learning without claiming efficacy from a generated explanation or self-reported understanding.

TRIAD is a Meridian **working name**, not a pre-existing scientific theorem. The research basis is structural alignment/structure-mapping, analogical encoding, relational abstraction and learning transfer (Gentner 1983; Gentner et al. 2004/2009; Gray & Holyoak 2021). This architecture is an experimental engineering synthesis, not a validated composite psychometric instrument.

## Model A — constrained relational graph alignment

Let the **target** (T=(V_T,R_T)) and analogies (A_i=(V_i,R_i)), (i∈\{1,2\}), be directed typed multigraphs. A typed relation (r(u,v)) may be dependency, cause, enables, requires, precedes or constrains. Require separately reviewed mappings (f_i:V_T^{\rm mapped}\to V_i).

For each candidate mapping define:

```text
covered_i = Σ_{r(u,v) ∈ R_T} w(r) · indicator[r(f_i(u), f_i(v)) ∈ R_i]
broken_i  = Σ_{r(u,v) ∈ R_T} w(r) · indicator[an analogy asserts a contradictory relation]
score_i   = covered_i − λ·broken_i − μ·unsupported_inferences_i
```

This is an **illustrative design objective**, not an established empirical score; (w,\lambda,\mu) require independent calibration. Mark safety/causality relations as CRITICAL and require every such relation to be preserved or explicitly delimited. Use SME-like constraints: corresponding relations must have corresponding arguments; favour coherent higher-order relational systems over isolated attribute matches.

The useful **shared structural core** (K) is the explicitly reviewed set of target relations mapped correctly by *both* analogies. Require structural agreement on K and **surface diversity** between (A_1,A_2). No assertion that the whole graphs are isomorphic; analogies have deliberate boundaries.

Reject if:
- both analogies are cosmetic paraphrases of the same story;
- a critical causal arrow reverses or contradicts itself;
- a missing dependency is presented as optional;
- disanalogies are absent or the learner infers facts from false correspondences.

## Model B — information bottleneck and minimum sufficient abstraction

Let (X=(T,A_1,A_2)) denote the **teaching evidence**, (Y) denote correct answers on held-out transfer tasks and (Z) the learner's abstract representation. As a *theoretical objective*:

```text
maximize I(Z;Y) − β I(Z;X)
```

Keep transferable task-relevant information, compress irrelevant surface detail. This is a conceptual application of information bottleneck, **not** a claim that an individual student's mutual information can be computed from one lesson. In early deployment, use observed explanation quality, far-transfer errors and retrieval instead of unverifiable MI numbers.

A succinct learner abstraction should recover the relationship:
`rules + checkpoint + complete ordered changes + accessible dependencies -> reconstructable continuation`.
But it must retain the assumptions, not a misleading promise of universal reconstruction.

## Model C — Bayesian belief revision and calibrated learning state

Maintain a probability distribution over *hypotheses about what the learner understands* (H), updated by independent transfer-task outcomes (O):

```text
p(H | O) ∝ p(O | H) · p(H)
```

Observations across analogies are dependent: do **not** multiply two apparently supporting stories as if they were independent evidence. Knowledge tracing (Corbett & Anderson 1994) can estimate evolving skill mastery while explicitly allowing guesses and slips, but its assumptions need validation with the target population. No self-certified `MASTERED` from the lesson generator.

For calibrated assessment, a two-parameter logistic IRT model may estimate the probability that learner `l` solves item `j`:

```text
P(correct[l,j]) = sigmoid(a[j] · (theta[l] − b[j]))
```

`theta`: latent competence; `a`: item discrimination; `b`: difficulty. Requires enough actual response data, a valid measurement model and independent scoring. Until calibrated, report **raw response rates, uncertainty and UNKNOWN mastery**, not a fictional precise competence score.

## Model D — causal evaluation of TRIAD, not a decorative score

Measure treatment effect `τ = E[Y(1) − Y(0)]` for unseen, rubric-scored transfer, ideally via pre-registered random assignment:

- CONTROL: precise canonical explanation without analogies.
- A: canonical + one analogy.
- TRIAD: canonical + two deliberately diverse, guided and boundary-marked analogies.
- Match lesson time where feasible; also record total burden, latency, accessibility issues and provider cost.
- Primary outcome: **independently blinded, previously unseen transfer**.
- Secondary: delayed retention, false-positive transfer, ability to name assumptions, time-on-task, accessibility/learner burden and cost.
- Counterexample tasks must tempt a misleading analogy inference.
- Repeated tasks and small samples can confound results: pre-register cohorts, confidence intervals, missingness handling and stopping rules. A null/negative TRIAD effect is legitimate research yield if method and results are reproducible.

Do not force TRIAD on every lesson. Progressive alignment matters; beginners may need one close analogy first, while advanced learners may benefit from more distant examples. Two analogies do not mathematically guarantee intuition or learning.

## Worked demonstration — the Meridian regenerative seed

**Precise target:** for a specified deterministic/versioned subsystem at time (t), conditional reconstruction requires a trusted rules/schema bundle (K), a verifiable checkpoint (C_{t_0}), complete ordered authenticated events (E_{(t_0,t]}), and accessible external dependencies (D_t):

```text
state[t] = Replay(K, C[t0], E[(t0,t]], D[t])
```

`Replay` must be validated by independent readback, and a conditional recovery guarantee depends on explicit failure model, completeness, determinism/captured nondeterminism, durable storage and continuing authority. No fixed-size magic seed can regenerate arbitrary missing entropy or external state. These are conditional engineering requirements, not guaranteed by metaphor.

**Analogy 1 (garden):** DNA/rules, reserve/checkpoint, growth/environment. Broken edge: a seed does not encode every historical event or generate a bitwise identical mature tree.

**Analogy 2 (orchestra):** score/rules, saved bar/checkpoint, performance ledger/events, musicians/instruments/runtime. Broken edge: a score without the exact recorded performance cannot reconstruct the historical sound; interpretation introduces nondeterminism.

**Transfer test, analogy-free:** migrate an encrypted longitudinal business transaction ledger to a new authorized runtime. Ask the learner to identify what breaks if historical changes, the decryption key or executable schema migration is absent. Grade the model of state, rules, events, dependencies, authorization and irrecoverable loss — not the learner's use of 'seed' or 'music'.

**Falsifier:** present a superficially similar example with an incorrect causal dependency; reject the response if the learner follows the story rather than the rule.

## Lesson contract (draft)

```yaml
lesson_id: triad.<domain>.<concept>.<version>
goal: "Learner independently solves unfamiliar case under correct assumptions"
subgoals: [define, align, critique, transfer, revisit]
canonical: {relations: [], assumptions: [], falsifiers: [], expert_review: null}
analogy_1: {domain: "", relation_mapping: [], breaks_at: []}
analogy_2: {domain: "", relation_mapping: [], breaks_at: []}
shared_core: {reviewed_relations: [], unsupported_inferences: []}
assessment: {unseen_transfer: null, delayed_transfer: null, disanalogy_probe: null}
experiment: {cohort: null, comparator: null, registered_metrics: [], blinded_evaluator: null}
evidence: {lesson_source_sha: null, independent_result_uri: null, measured_cost: null}
verdict: "UNVERIFIED"
```

## Producer-first admission and lifecycle

1. Validate exact canonical claims, assumptions and analogical relational alignment *before* learner presentation. Do not output false causal mappings.
2. Generate and present both analogies with limits, but allow learner to request simpler or alternate examples.
3. Use independently scored novel transfer; capture actual response evidence, not teacher/LLM self-assessed confidence.
4. Return `UNKNOWN` if real learner, blinded scoring, valid outcomes or cost observations are missing.
5. Reuse existing HELM evaluation, Optimus measurement, KARMA obligations, FLOW custody and Genesis readback, not a second grader, evidence ledger or dashboard. Commercial education claims require separately verified, suitably powered real-world evidence.
6. Preserve negative cases as reusable research and training IP, with content/version/attribution provenance.

## References
- Gentner (1983), "Structure-mapping: A theoretical framework for analogy", Cognitive Science. https://doi.org/10.1016/S0364-0213(83)80009-3
- Gentner, Loewenstein & Thompson (2004), "Analogical encoding: Facilitating knowledge transfer and integration". https://groups.psych.northwestern.edu/gentner/papers/GentnerLoewensteinThompson04.pdf
- Gentner et al. (2009), "Reviving inert knowledge", Cognitive Science. https://doi.org/10.1111/j.1551-6709.2009.01070.x
- Gray & Holyoak (2021), "Teaching by analogy: From theory to practice". https://doi.org/10.1111/mbe.12288
- Corbett & Anderson (1994), "Knowledge tracing: Modeling the acquisition of procedural knowledge". https://doi.org/10.1007/BF01099821
- Information bottleneck: https://pmc.ncbi.nlm.nih.gov/articles/PMC10968930/

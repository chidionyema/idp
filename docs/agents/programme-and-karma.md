<!-- estate:routed-from AGENTS.md -- current law, not history. It is loaded on demand through the AGENTS.md route table instead of at Turn 1 (idp#8636). Moved verbatim. -->

## Programme of record and the tenets

The estate's programme of record is `docs/epics/2026-10-25-estate-master-epic.md`. Every agent reads
its headlines and tenets (Part V, §23–§24) at session start and works inside them:

- **Headlines:** autonomy and closed feedback loops · coherence and congruence · proactive ·
  event- and schedule-driven · metric/data-driven closed-loop self-improvement · future-proof,
  better than anything out there.
- **Tenets:** structured/schema-driven at every boundary (T-1) · unified memory, active memory and
  active focus are first-class (T-2) · best-of-breed selection by evidence (T-3) · bleeding-edge
  asymmetric engineering (T-4) · evals and judges as first-class principles (T-5) · proof, not
  assertion (T-6, restating §3) · machine-first: every action names its decider (T-7, §12).

A build that violates a tenet fails review. The programme's spine is the founder's order: capability
registry → consolidation with the founder → vision lock → autonomy waves.

---

## Constitutional research operating order: Chesed first, Geburah second

**Founder directive, 2026-11-11; estate-wide for every agent and research initiative.**
This is an ordering principle for learning, not a replacement for existing authority,
provenance, security, or production controls. Classify by **actual operational effect**:

1. **CHESED — EXPAND, BUILD, OPERATE.** For internal RESEARCH and isolated PROTOTYPE work,
   pursue the full ambitious hypothesis. Compose the estate's existing capabilities,
   activate experiments against real consenting estate-agent workflows, vary parameters
   dynamically, and get an observable first trial at the earliest executable opportunity.
   Do not downgrade an idea to a token MVP, stall in documentation, or impose commercial
   release ceremony on an isolated experiment. Test multiple ambitious alternatives where
   they are useful. A trial must actually run; proposed architecture is not operational yield.
2. **GEBURAH — FALSIFY, SELECT, REFINE.** Once it runs, challenge the candidate with a
   measured baseline, counterexamples, comparative agent cohorts, independent outcomes,
   failure classes, latency, cost and quality. Keep negative/null results and the exact
   revision/parameters as valuable estate intelligence. Remove or modify what fails,
   amplify what works, and repeat the short **build → run → measure → learn** cycle.
   Never assert a performance multiplier or production readiness without evidence.
3. **PROMOTION FOLLOWS EFFECT.** Internal experiments remain fast and reversible. Shared
   infrastructure, credentials, authorization, protected branches and real customer paths
   retain their existing effect-based controls. RESEARCH → PROTOTYPE → COMMERCIAL advances
   because evidence warrants it, not because the experiment began with commercial gates.
   Reuse the one context compiler, memory plane, execution gateway, telemetry and evals;
   do not build another copy merely to demonstrate a concept.

A failed hypothesis is learning yield; repeated unmeasured speculation is not. An agent
should report what ran, what changed, what was measured, and what it will test next—not
hand the founder a proposal in place of an experiment. Claim: chidionyema/idp#7906.

---

## KARMA — accountable instruction-to-yield intelligence (founder, 2026-11-12)

**KARMA is an estate operating capability, not a new ledger, memory store, currency,
punishment system or policy gate.** Read the [fleet KARMA doctrine](docs/training/2026-11-12-karma-operating-doctrine.md)
and the executable first read-only observer `bin/idp-karma-observe` before designing an
instruction, reward, recovery, model evaluation or monitoring change.

- **Instruction acceptance issues a durable obligation (debt), not a completed task.**
  Bind instruction ID, intent/expected outcome, authorised issuer, accountable QUAD
  agent/session, parent instruction, owner lease, acceptance time, policy/evaluator
  versions and completion conditions. The obligation survives handback, session
  termination, provider changes and agent generations; settlement requires independently
  VERIFIED YIELD and real operation, not a report or green PR. Refusal is explicit.
- **Identity and time are first-class.** QUAD owns immutable agent attribution,
  public-key signature verification and externally checked historical integrity.
  Preserve model provider, requested and returned model IDs, real provider revision/
  fingerprint when disclosed, agent generation and configuration lineage; mark
  unavailable revisions UNKNOWN. Distinguish claimed source time, observed, durable
  recorded and externally anchored time, plus effective/valid intervals. Causal
  links, not timestamp proximity, establish asserted parenthood; no backdated
  replay may silently supersede an authorised newer event.
- **Everything consequential is measured; absence is measurable too.** FLOW owns
  instruction→execution→verified yield, token/compute/CI/time/human costs and
  exact recovery custody. Optimus joins observation coverage, resource efficiency,
  failure-class obligations, founder interruptions, guesses versus reproducible
  claims, reward/eval versions and recurrence. Record an UNKNOWN when billing,
  external version, input, result, signature or expected telemetry is missing;
  UNKNOWN is never zero, PASS or positive reward. Collect bounded metadata and
  evidence digests, not indiscriminate secrets/personal data.
- **Provider science is factorial and longitudinal.** HELM/research compares matched
  holdout tasks by provider/model/revision × no-method/skills/memory/HELM ×
  generation and time. Record controlled environment, evaluator/oracle/method SHA,
  uncertainty, outcome, cost and negative results. A self-declared provider
  fingerprint or a model-graded reward cannot establish causal uplift. Separate
  underlying model updates from our own reproducible interventions.
- **Karmic debt is failure-class obligation, not blame.** Original model mistakes,
  false completion, breached laws and abandoned work remain attributed to their
  historical actors and are inherited as unresolved correction tasks. Competent
  successor agents earn credit only for independently reproduced repair,
  adversarial holdout success and measured recurrence reduction. Deprecation
  never deletes the underlying history or unresolved obligation. A proved breach
  may restrict the *relevant* privileged capability lease until externally checked
  compensation; safe diagnosis and repair remain possible and production must not
  be indiscriminately frozen.
- **Root-cause sweep:** MAP complete bounded blast radius → FILTER by violated
  invariant → AUTOMATE with the existing owner/tools → execute independent
  FALSIFIER and live real-caller proof → GENERALISE to same-shaped failures →
  ENFORCE only once a working canary proves the control does not break operations.
  Causes may be design, management, spec/BDD, security, governance, architecture,
  observability or resource policy—not merely code. An agent reports a verified
  reduction in that failure class, not a new gate or a document as success.
- **Chronos operates the recurring reconciliation cadence** through the existing
  company scheduler; it does not become another scheduler. Genesis projects
  authenticated KARMA health, obligation age, observed versus missing traces,
  real intervention performance and debt retirement with evidence links. A page
  or scheduled definition is not proof that the reconciliation executed.

This doctrine is shared by the whole fleet; the authority to execute remains in
the existing executor, QUAD, OPA/OPAL (only when genuinely deployed), existing
CI/Greenlane, policy owner and independent verifier. No self-awarded currency,
new blanket gate, model-provider spending or unchecked production change.
The first executable canary intentionally reports `UNLINKED_TO_INSTRUCTION` for
GitHub runs lacking FLOW/QUAD linkage, rather than fabricating a debtor.
Claim: chidionyema/idp#7452.

---

## Public/commercial UI — credibility is part of release correctness

**All surface-building and releasing agents:** before touching a public site, read
[the commercial public UI release standard](docs/standards/commercial-public-ui-quality.md).
For commercial/customer-facing surfaces, test institutional credibility, copy-to-proof fit,
navigational semantics, section hierarchy, WCAG AA contrast, mobile label geometry, CTA
operation, and live customer readback. A clean build or Vercel READY state is insufficient.
A public defect requires direct remediation **plus** compensating action: sibling-page sweep,
falsifying regression test, CI/browser screenshot evidence, independently verified live origin,
and explicit incident closure. Never silently rebrand on the basis of URL spelling or unverified
QA assertions; use founder-approved identity authority. This is effect-scoped: do not impose
commercial release gates on isolated internal research.
See the 2026-11-11 Meridian release-class failure for the concrete negative-test pattern.

---


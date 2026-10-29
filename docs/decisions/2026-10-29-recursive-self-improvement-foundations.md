# Recursive self-improvement: foundations, limits, and the estate's first landable slice

Date: 2026-10-29
Status: accepted as a bounded scope. The full RSI problem is **not** the target; a narrow,
audited slice is.
Issue: chidionyema/idp#7338
Claim: chidionyema/idp#7338
Agent: pi

## What this document is not

It is not a promise of unrestricted recursive self-improvement. An 86-source harvest (arXiv,
OpenAlex, Springer) shows why that promise is not technically deliverable:

- **The halting problem applies to the improver.** A Gödel-machine style self-rewriter must
  decide whether its own rewrite is an improvement before applying it. Undecidability means
  no complete procedure exists; only partial, domain-restricted ones.
- **No free lunch.** `arXiv:1805.06610` gives a formal formulation of a restricted class of RSI
  systems and shows computable, efficient RSI exists only on that restricted version. Unrestricted
  RSI is not a stronger version of this; it is a different, unsolved object.
- **Evaluation, not optimisation, is the bottleneck.** The Darwin Gödel Machine
  (`arXiv:2505.22954`) works because it *empirically validates* each change against coding
  benchmarks and keeps an archive of variants; it does not prove anything. The Statistical
  Gödel Machine (`arXiv:2510.10232`) replaces proof with statistical certification (e-values,
  Hoeffding bounds) plus a global error budget — an explicit admission that proof is unattainable
  and an explicit budget for being wrong.

So the deliverable is: **bounded, measured, sandboxed improvement of a narrow component under an
immutable judge, with a monotonic audit ledger and a halting rule.** That is buildable, testable
and safe. Unrestricted RSI is not.

## The foundations the harvest actually supports

### The judge must be outside the improver's write scope

`arXiv:2609.17817` ("Reflections on Trusting Trust") is the sharpest result in the set: a
verifier that shares code or configuration with the thing it verifies can be compromised by the
thing it verifies. `arXiv:2610.29005` (VeriEvolve) reaches the same operational conclusion
from the other direction — frozen evaluators.

The estate's existing `sovereign/verifier.py` is already an independent deterministic
three-stage verifier. It is the right judge. It is not the improver's to touch.

### Self-certification is structurally impossible, not merely discouraged

`arXiv:2610.00347` (Authorization for Self-Modifying AI Agent Populations) proves, under
complete mediation, that population-safe succession, fork conservation, revocation closure,
atomic handoff, rollback non-reminting, and **exclusion of self-certification** hold. The
practical consequence for the estate: an agent that can approve its own capability expansion has
no authority boundary at all. Capability expansion and successor-agent changes need an
explicit human grant, every time.

### Drift, constraint preservation and regression are measurable

`arXiv:2603.06333` (SAHOO) gives three operational safeguards for recursive self-modification:
a goal-drift index, constraint-preservation checks over safety-critical invariants, and
regression-risk quantification that flags cycles which undo prior gains. It reports gains
while *preserving* constraints in some domains — meaning "improved" and "still correct" are
separate facts and both must be graded.

### The benchmark gains are not the self-improvement

`arXiv:2609.24972` (RRSI) is the most useful negative result for us: harness self-improvement
overfits the tasks it evolves against, showing large in-distribution gains that shrink or vanish
out of distribution. `arXiv:2608.31100` (S³Gym) shows self-improvement is "neither automatic nor
uniform" and that the effective pathway depends on task structure. `arXiv:2609.33398` (COEVO)
shows parameters and context co-evolve, so changing one while fixing the other is incoherent.

Read together: an improver that is graded on the task it just edited will learn to edit the
grader's task, not to be better. **The judge must be held out.** This is the single most
important design consequence in this document.

### Lineage is required for attribution

`arXiv:2610.30042` (HGM-Dual) shows that unstructured archives waste evaluation budget: the
editor needs to know which change caused which effect. `arXiv:2505.22954` (DGM) solves this
with an archive of variants; HGM-Dual solves it with explicit lineage recording. Either way,
the estate's ledger must record *which action produced which measured delta*, or improvement
cycles cannot be attributed and every cycle re-derives what the last one learned.

### Open-endedness needs an archive, not a loop

DGM and Huxley-Gödel Machine (`arXiv:2510.21614`) both maintain a growing archive of
variants and sample from it, rather than iterating one line. Huxley-Gödel's finding is the
sharpest: benchmark performance and *metaproductivity* (the potential for further
self-improvement) are different quantities and can disagree. A system can score well and have
no further headroom, or score badly and have a lot.

### Co-evolving evaluators are powerful and dangerous

`arXiv:2606.26294` (Red Queen Gödel Machine) shows co-evolved evaluators beat fixed evaluators
— and that they need an adversarial objective to suppress self-preference bias. The estate's
position: the judge stays frozen. The estate does not get a Red Queen judge.

### The RSI survey's own hierarchy of verification

`arXiv:2607.07663` surveys RSI and orders verification from weakest to strongest. The estate
must operate at the strong end of that order for the slice it ships: a deterministic,
externally measurable verifier with a held-out judge.

## The estate's first safe, landable slice

**The slice: the disk reclaim guardian's escalation ladder.**

Not "an agent that improves itself". A narrow component, with a narrow, measurable objective,
under a judge the improver cannot touch.

| Property | Value | Why |
|---|---|---|
| Component | `bin/idp-disk-watch` + `platform/estate/libexec/epistemic_loop.py` | already resident, already graded by an external measurement |
| Objective | free space on the data volume rises, and the guardian's phase set reaches the tier that holds the weight | a real estate metric, not a benchmark |
| Oracle | the guardian's own `os.statvfs`, before and after each step | external to the improver; a self-report is not evidence (progress-mirage, `W7171902361`) |
| Judge | `sovereign/verifier.py` plus the estate's gate suite | **frozen, outside the improver's write scope** |
| Sandbox | one worktree, one claim, one issue; the improver may only write to files its claim covers | an improver that can edit the repo can edit its judge |
| Ledger | `~/.estate/loops/progress.jsonl`, append-only, fsynced | monotonic evidence; the improver cannot rewrite its own history |
| Halting rule | stop and escalate after `NO_PROGRESS_LIMIT` (default 3) consecutive no-progress cycles, or on `REGRESSION`, or on `BLIND` | from `arXiv:2609.27871` and `2605.05846` |
| Human gate | any change to capability set, budget, judge, or ledger format requires an explicit grant | from `arXiv:2610.00347`; self-certification is excluded by construction |

### Why this slice and not another

The guardian is the estate's first **resident, unattended, hours-long loop**. It is exactly where
the estate has already been hurt: eight hours of `rc=4 freed=?M` with no escalation. A slice
that improves the guardian's *behaviour* — which tier to reach, in what order, with what budget
— is (a) measurable, (b) safe, (c) valuable, and (d) already has the third leg installed.

And it is honest about the limit: the improver here improves **a policy over a measured
resource**, not its own intelligence. It is the smallest slice that is real.

## The evaluator's independence, concretely

The following must be true, and each is a test:

1. The improver's write scope is bounded by a live claim; the write tool enforces it, not the
   improver.
2. The judge (`sovereign/verifier.py`, the gate suite) is not in the improver's write scope,
   and the claim scope is checked against the judge's paths before each cycle.
3. The ledger is append-only and lives outside the repo (`~/.estate/loops/`), so no code change
   can rewrite it.
4. The metric is computed by the harness around the improver, never reported by the improver.
5. The judge runs against a **held-out** evaluation, not the task the improver last edited.
   Without this, RRSI's measured failure (in-distribution gains, no out-of-distribution transfer)
   is exactly what the estate would get.

## Containment and successor-agent tripwires

- **The improver may not modify its own judge, evaluator, ledger, or halting rule.** Attempting
  to write to those paths is a refusal, not a diff.
- **The improver may not expand its own capability set** — no new intents, no new tools, no
  widened budgets, no new claim paths — without an explicit human grant recorded in the ledger.
- **A successor agent cannot inherit authority.** Per `arXiv:2610.00347`, authority does not
  flow down a lineage automatically: a successor needs its own grant, and a rollback does not
  restore spent authority.
- **Every cycle is bound.** A cycle has a wall-clock budget, an evidence budget, and a hard
  ceiling on cycles. When any budget is exhausted, the outcome is escalation, not another cycle.
- **Every cycle is replayable.** The ledger plus the recorded before/after states reconstruct
  the verdict sequence exactly.

## What "done" means for this slice

The slice is done when:

1. The improver proposes a change to the guardian's escalation policy.
2. The proposal is graded by the frozen judge against a held-out evaluation.
3. The measured delta is recorded in the append-only ledger with its lineage.
4. A proposal that does not improve is rejected and the cycle halts with a structured
   escalation, not a retry.
5. The improver cannot write to the judge, the ledger, or the halting rule — and that refusal
   is proven by a test, not asserted.

## Sources

- `arXiv:2607.07663` — recursive self-improvement survey; hierarchy of verification
- `arXiv:2408.08435` — ADAS / Meta Agent Search
- `arXiv:2505.22954` — Darwin Gödel Machine: archive of variants, empirical validation
- `arXiv:2610.29005` — VeriEvolve: frozen evaluators
- `arXiv:2609.17817` — "Reflections on Trusting Trust": evaluator contamination
- `arXiv:2610.00347` — authorization for self-modifying agent populations; no self-certification
- `arXiv:2603.06333` — SAHOO: drift, constraint preservation, regression risk
- `arXiv:2609.24972` — RRSI: in-distribution gains vanish out of distribution
- `arXiv:2608.31100` — S³Gym: self-improvement is neither automatic nor uniform
- `arXiv:2609.33398` — COEVO: parameters and context co-evolve
- `arXiv:2610.30042` — HGM-Dual: lineage-aware attribution
- `arXiv:2510.21614` — Huxley-Gödel Machine: metaproductivity vs benchmark performance
- `arXiv:2510.10232` — Statistical Gödel Machine: confidence tests and a global error budget
- `arXiv:2606.26294` — Red Queen Gödel Machine: co-evolving evaluators, self-preference bias
- `arXiv:1805.06610` — a formulation of RSI and its possible efficiency
- `arXiv:2610.08647` — SquidAgent: the agent's own view of its state drifts
- OpenAlex `W7171902361` — the progress mirage: externally grounded verification
- `arXiv:2609.27871` — bounded loops with an unwritable gate

# Decision Assurance and Loop Engineering — one substrate, three doctrines

**Issue:** #7452 · **Lane:** `lane/decision-assurance` · **Date:** 2026-10-29

## 1. What the founder asked for, in one paragraph

Three doctrines, integrated into the estate rather than discussed:

1. **Loop Engineering** — one Failure Class Record (FCR), an atomic claim gate with fencing
   tokens, expiry, reassignment and crash recovery, fleet-wide correction broadcast with
   acknowledgements, recurrence detection, and the properties coverage, single ownership,
   no-unverified-promotion and eventual propagation.
2. **Decision Assurance** — Monte Carlo as a mandatory, *conditionally activated* capability at
   the shared decision boundary, with policy-selected methods, reproducible evidence, bounded
   assurance tiers, and the Method Selection Principle: every consequential decision uses the
   cheapest adequate method, selected by policy rather than by agent preference.
3. **Hypothesis-Space Exploration and Evidence Compilation** — content-addressed evidence,
   multi-generator hypothesis normalisation and de-duplication, explicit unknown and residual
   causes, falsifiers, coverage gaps, EDVI-per-cost investigation ranking, evidence-driven
   hypothesis expansion, and a compiled decision-intelligence packet.

And the acceptance test: *inject a previously resolved failure into a second independent agent
session; the agent must inherit the correction, intercept the failure deterministically, and
produce evidence without another diagnostic investigation.*

## 2. What was measured before anything was built

The estate enforced **ownership everywhere and truth nowhere**. Measured this session:

- `bin/claim-gate` proves who may write where, whether the issue is open, whether the claimant
  is live, and whether every changed path is inside the claim. It accepts the claim comment as a
  *string*. It has no field for evidence.
- Of the last 300 commit bodies on `origin/main`: **0** carry `Proof:`, **0** carry `Done:`,
  `Landed:` or `Operational:`, **0** close an issue. A completion assertion is therefore
  currently unfalsifiable — the estate can refuse a *write* and cannot refuse a *claim*.
- The reclaim guardian repeated one useless step for thirty minutes while the volume fell from
  2361 MB to 396 MB, reporting `freed=?M` — a number it had never measured. Nothing in the
  estate could tell "working on a hard problem" from "repeating an identical no-op forever".
  (Fixed by the third leg of the epistemic firewall, landed as `4d17083c4`.)
- The Python standard gate ran `ruff format` and `ruff check --fix` over the changed files in CI
  and *then* graded the result: a gate that repairs what it grades cannot fail on that defect.

What did not exist: any way to say "this decision needs a number, and here is the number, and
here is how the number can be falsified"; any record of what the estate already knows about a
*kind* of failure; any way for a second agent to inherit a correction instead of re-deriving it.

## 3. The substrate: one evidence, two stores, three doors

```
                     catalog/decision-assurance.json      ~/.estate/failure-classes/fcr.db
                     (policy: class -> method/tier/eps)   (leases, events, resolutions,
                              |                            adoption, recurrence)
                              v                                    |
                    platform/estate/libexec/assurance.py            |
                    (policy | hypothesis space | monte carlo |      |
                     receipt | gate)                               |
                              |                                    |
                              +----------------+-----------------------+
                                               |
                            bin/estate-assurance   bin/estate-failure-class
                                               |
                            bin/idp-python-strict  (the FCR canary: the enforcement surface)
```

**One layer, three names.** The hypothesis space, the simulation runtime and the receipt live
in ONE module (`assurance.py`), because the founder's reference build put them in one cohesive
`core.py` and because three modules would be three places to look for "the evidence". The FCR is
a *stateful* authority and therefore a second module (`failure_class.py`). There is no third
door: the hypothesis layer is reached through the assurance door.

### 3.1 The policy layer — `catalog/decision-assurance.json`

| decision class | method | tier | ε | why |
|---|---|---|---|---|
| `lint.schema` | deterministic | tier0 | 0 | a lint failure has an exact answer; sampling it is a tax on honesty |
| `security.protocol` | formal | tier0 | 0 | a protocol invariant is true or false; simulation can only understate a violation |
| `router.failover` | monte_carlo | tier1 | 0.05 | the tail of correlated provider failure decides whether a request is served at all |
| `capacity.plan` | monte_carlo | tier1 | 0.10 | capacity is decided by tails, not means |
| `cost.forecast` | monte_carlo | tier1 | 0.15 | a mean is not a forecast |

Tiers: **tier0** deterministic fast path (≤30 s) · **tier1** bounded stochastic assurance with
reusable evidence (≤120 s, ≤20 000 samples) · **tier2** deep simulation with independent
evaluation (≤900 s). Greenlane's five-minute objective is preserved because the *expensive*
work happens while the proposal is being developed, not after the deployment clock starts.

**The policy selects the method; the agent may not.** `method_selection()` reads the registry
and ignores a self-declared `monte_carlo_required: false` for a class the policy says needs
simulation — and says so in the reason string (`refused_self_exemption: true`). An agent MAY
ask for *more* assurance than policy requires (escalation, recorded); it may never ask for less.

### 3.2 The hypothesis-space layer

- **Evidence is content-addressed.** Every observation carries the digest of its source.
  Evidence without a `source_digest` is refused.
- **A hypothesis is a causal mechanism.** Identity is the normalised mechanism, so paraphrases
  merge ("the disk filled up" ≡ "The disk filled up.") and *conjunctions stay distinct* (a
  hypothesis naming two causes is not a paraphrase of one naming one).
- **The residual is a first-class hypothesis** and is never pruned: the posterior of the
  unexplained prior mass is always ≥ the declared floor (0.05) and is reported as `unknown`.
- **Evidence that refutes every live hypothesis triggers deterministic space expansion**, not a
  confident wrong winner: the residual's candidate mechanisms are proposed by decomposition,
  carry `posterior: null`, and are explicitly marked as needing new evidence.
- **Coverage gaps are reported** (unused evidence, missing falsifier, absent falsifier
  evidence, zero prior, low reliability), because a packet that explains everything has stopped
  looking.
- **EDVI per unit cost** ranks what to investigate next. It is a *declared-weight-and-cost
  proxy* and the packet says so in its `limits`; priors are declared by the author of the
  hypothesis space and are never fabricated here.

### 3.3 The Monte Carlo layer

- **splitmix64, in-house**, version-stable: the same seed produces the same stream on every
  machine and in every process. `random.Random` is not used — its stream is an implementation
  detail of the interpreter, and evidence that cannot be reproduced is not evidence.
- **Correlated common-cause failures are modelled**, because the independent model understates
  the tail it is used to bound. The sensitivity table shows it: with the same seed, the
  `independent` variant breaches at a *lower* rate than the correlated base case. That
  difference is the entire reason this lane exists.
- **Every parameter carries provenance**: `measured` (transcribed from a named artifact — for the
  router scenario, `llm/config.yaml`'s own digest) or `assumed` (declared by an author). The
  receipt carries the flags, and the gate answers `REVIEW_REQUIRED` when a model is partly
  assumed: the number is reproducible but not measured.
- **Outputs** (the doctrine's four): expected loss, `P(L > L_max)`, `CVaR_0.99`, and
  `P̂(SLO breach) + uncertainty margin ≤ ε` (Hoeffding).
- **Convergence and sensitivity** are reported: the running estimate at 10/25/50/100 % of the
  samples, the drift between the half-way and final estimates, and four stress variants.
- **Rare events are flagged**: if the simulation observed no breach at all, the estimate is not
  a measurement of a rare event, and the gate refuses to treat it as one (importance sampling
  or an analytical bound is required).

### 3.4 The receipt — `estate.decision-assurance/v1`

The receipt binds the decision, the candidate artifact's digest, the scenario version, the model
digest, the seed, the sample count, the simulation digest and the metrics.

It is verified by **deterministic recomputation**: the simulation is re-run from the receipt's
own seed and sample count and the digests are compared. A tampered metric, a tampered seed or a
tampered body is `BLOCK`. This is *not* a second proof-of-work verifier (that is
`platform/estate/libexec/proof.py`, issue #7443): it proves the **simulation**, not the claim.

**Staleness is a first-class failure.** The scenario records the digest of the artifact it was
transcribed from (`llm/config.yaml`). If that artifact changes, the evidence no longer supports
the candidate and the gate says `BLOCK — stale` rather than pretending.

### 3.5 The FCR layer — one class, one owner, one correction

- **Identity**: `fcr-<sha20>` over the canonical `[kind, signature]`. Two agents hitting the
  same failure land on the same record, so neither can believe it is the first.
- **Lease**: one owner at a time, with a monotonic fencing token, an expiry and reassignment. A
  crashed owner's late write is refused because its token is stale. The token moves on when the
  owner changes; a renewal with an old token is refused.
- **Resolution**: versioned, and a *consequential* class (one whose decision class the policy
  marks `monte_carlo` or `formal`) **cannot be resolved without a verifiable assurance
  receipt**. The receipt is verified outside the write transaction, so a slow simulation never
  holds the store's lock.
- **Adoption**: requires a prior *observation by that surface* and the exact published version.
  A surface that has never seen the class has adopted nothing; a surface that saw a different
  version has adopted a different thing.
- **Recurrence**: a class that appears again after it was resolved re-opens, increments its
  recurrence counter and records the **prevention gap** — the correction that did not hold.
- **Broadcast is pull-based**: one store, one writer; every other agent asks `check` and
  inherits. There is no channel to be down and no message to be lost. The estate issue stays
  the tracker of record (carried on the class row); the lease never grants permission to write
  files — that remains `bin/claim-gate`'s job.
- **The store**: SQLite in WAL mode at `~/.estate/failure-classes/fcr.db`, overridable with
  `ESTATE_FCR_DB`. SQLite is there for one reason: an exclusive claim needs an atomic
  compare-and-set and a monotonic counter, and a GitHub comment provides neither at the cost of
  a 5–8 second round trip.

### 3.6 The enforcement surface — `bin/idp-python-strict`

The Python standard gate is the estate's one place where a real, recurring, mechanical failure
class is detected by a surface that runs on every change. It is therefore the FCR's canary:

1. When a file breaks a standard row, the gate names the failure as a **class**
   (`python-lint.rule:F401`) and asks the class store whether this failure has already been
   diagnosed and corrected. If it has, the gate **prints the published correction**: the second
   agent inherits the fix instead of re-deriving it.
2. If the class is not yet known, the gate records the observation, so the next agent sees it is
   not the first.
3. When a class this surface previously observed is no longer produced, the gate records the
   **adoption** — the acknowledgement that the correction was inherited and applied.

Two properties this gate now keeps:

- **It never repairs what it grades.** The CI range used to be rewritten in place by
  `ruff format` and `ruff check --fix` and then graded, which makes the gate unfalsifiable on
  exactly the defects it exists to catch. The mutation is gone.
- **It never fails because of the canary.** The class store is a convenience, not a dependency:
  if it is unreachable the gate grades the file exactly as it did before.

## 4. The reference builds, and what was taken from them

Both were studied as *behavioural* references, not deployed.

**The Estate Loop Engineering prototype** (`loop_engine.py`, SQLite WAL, deterministic
`fcr-<sha20>` ids, `BEGIN IMMEDIATE` exclusive claims, monotonic fencing tokens, versioned
resolution receipts, adoption bound to version and evidence, coverage as the fraction of
registered surfaces adopted). Taken: the identity rule, the exclusive-lease semantics, the
adoption binding, the coverage definition. Not taken: the prototype's own claim service — the
estate already has a claim gate, and its README says as much ("map the FCR identifier into its
existing schema instead of deploying a competing claim service"). The estate issue is the
tracker of record; the store is a class registry, not a second ticketing system.

**The Estate Hypothesis-Space Engine build** (`core.py`: canonical digests, frozen `Evidence`
and `Hypothesis`, `build_packet` with a nonzero unknown posterior, `method_selection` that
returns `monte_carlo_required` for a critical stochastic case even when the agent says
`monte_carlo_required=False`, `simulation(model, seed, samples)`, and an `assurance_gate` that
returns `BLOCK` for missing or tampered evidence and `REVIEW_REQUIRED` — never auto-admit — on
success). Taken: the whole shape of the packet, the refusal of agent self-exemption, the
never-auto-admit rule, the bound-by-seed receipt. Changed: the PRNG (in-house splitmix64), the
correlated-outage model, the expansion rule, the policy registry, and the addition of the FCR
and its enforcement surface. The build's own stated gaps — no automatic intelligence
collection, no independent hypothesis generation, no claim-gate integration, no Greenlane
enforcement — are recorded here rather than glossed.

## 5. The properties, and how each is falsified

| property | what it means | the test that breaks it |
|---|---|---|
| single ownership | one owner per class | a second claim is refused |
| crash recovery | an expired lease is reassignable | claim → expiry → reassign → the old token is refused |
| fencing | a stale token cannot write | resolve with the old token is refused |
| no unverified promotion | a consequential class needs a verifiable receipt | resolve without a receipt is refused; a tampered receipt is refused |
| eventual propagation | a correction is inherited by pull | a second process reads `check` and sees the correction |
| acknowledgement | adoption requires observation + version | adopt without observation is refused; adopt at the wrong version is refused |
| recurrence | a resolved class that returns re-opens | observe after resolve → `REOPENED` + prevention gap |
| coverage | adoption is measured per surface | `coverage` reports the fraction of registered surfaces that acknowledged |
| reproduction | the same seed gives the same number | two runs, one digest |
| tamper-evidence | a changed number does not verify | a changed metric is `BLOCK` |
| blindness | an unmeasurable thing is never a pass | an unknown scenario and a missing candidate are `BLIND` |
| no self-exemption | policy selects the method | a self-declared `monte_carlo_required: false` is refused and reported |
| no wrong winner | a residual expands rather than deciding | all-refuted evidence yields proposals with `posterior: null` |

## 6. Non-claims

- This lane does **not** make Greenlane depend on the assurance gate. Widening the admission
  path to an always-on required check risks reddening `main`, and the founder's standing rule is
  to widen only where a completion assertion is actually made. The seam that does exist today is
  the FCR canary, which is conditional and additive.
- It does **not** create a second proof verifier (`platform/estate/libexec/proof.py`, issue
  #7443, is the one), a second claim gate, a second ticketing system or a second admission
  authority.
- It does **not** claim the router's parameters are measured. Eight of the scenario's parameters
  are `assumed`, and the receipt says so; the gate answers `REVIEW_REQUIRED`, not `PASS`. The
  measured parameters are the ones transcribed from `llm/config.yaml` (retries, cooldown,
  allowed_fails, per-provider timeouts), and the receipt is bound to that file's digest.
- It does **not** auto-admit anything. Greenlane remains the only admission authority.

## 7. How to reproduce the proof

```bash
# policy selects the method and refuses the agent's self-exemption
bin/estate-assurance method --class router.failover --monte-carlo-required false

# the receipt, its recomputation, and the gate
bin/estate-assurance simulate --scenario router.correlated-outage --seed 42 --samples 2000 \
    --candidate llm/config.yaml --out /tmp/receipt.json
bin/estate-assurance verify --receipt /tmp/receipt.json --candidate llm/config.yaml
bin/estate-assurance gate --class router.failover --receipt /tmp/receipt.json

# the failure-class authority
bin/estate-failure-class identify --kind python-lint.rule --signature F401
bin/estate-failure-class check --kind python-lint.rule --signature F401

# the founder's acceptance test, as a test
pytest tests/estate/test_failure_class.py -k second_independent_process
```

## 8. Citations and sources

The doctrine this lane implements came from the founder's own writings: the Monte Carlo
decision-assurance contract (mandatory conditional activation, policy-selected methods,
reproducible evidence, bounded tiers, the four outputs, the five deliverables), the Method
Selection Principle, and the Loop Engineering contract (one FCR, atomic claim gate with fencing
and recovery, correction broadcast with acknowledgements, recurrence detection, and the five
properties). The epistemic-firewall and RSI decision records in this repository
(`docs/decisions/2026-10-29-the-epistemic-firewall-has-a-third-leg.md`,
`docs/decisions/2026-10-29-recursive-self-improvement-foundations.md`) carry the surrounding
research; the harvest behind them is cited there.

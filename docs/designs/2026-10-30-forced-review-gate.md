# The forced-review gate: a change to a founder surface or a critical service must be reviewed

Status: proposed, decision core landed, not yet wired as a CI gate.
Date: 2026-10-30.
Claim: chidionyema/idp#7544.
Agent: pi-design-cores.

## The gap, stated as a fact

The estate has exactly one gate for the paths only the founder may change:
`bin/idp-ci-guarded-paths`, which refuses a change to `.githooks/`, `bin/idp-auth`,
`bin/idp-guarded-paths`, `bin/idp-ci-guarded-paths` and the kyverno/otel policies without a
founder signature. The list is seven entries, and it is deliberately small: a founder signature
is an expensive authority to spend on every edit.

Everything else that can hurt the founder has no gate at all. `/fleet`, the voice engine, the
founder decision door, the executor, the merge lane, the router, the deployment manifests and
the governance layer can all be changed by any agent holding a claim. The only review is the one
an agent remembers to run. The estate's own law names this shape:

> "A gate that cannot fail is not a gate." -- AGENTS.md section 9, principle 1.

Today there is no gate here to fail.

## The design in one paragraph

A machine-readable inventory names the founder surfaces and the critical services. When a change
touches one of them, it may not land without a **review receipt**: a signed-by-digest JSON
document produced by the estate's existing four-tier review pipeline, bound to the exact commit
under judgement and to the exact base it was reviewed against. The decision is made by a small
pure module, `platform/estate/governance/review_gate.py`, whose entire job is to answer one
question -- *may this change land without a passing review?* -- and to answer "no" whenever it
cannot tell.

## Why it reuses `code-review` instead of writing a review engine

`platform/estate/intents/code-review.yaml` already runs T0 (lint), T1 (heuristics), T2 (LLM
judgment) and T3 (deterministic verification of every T2 finding), and writes each tier's JSON
under `$HOME/.estate/review/latest/`. T3 is the gate inside the gate: "stochastic judgment
proposes; deterministic verification disposes".

A second review implementation would be the stitching AGENTS.md section 6 forbids. So the gate
consumes the engine's output and decides only the landing question. The review engine produces
findings; the gate decides whether a reviewed SHA is acceptable. Two concerns, two files.

## The inventory

`platform/estate/governance/founder-surfaces.yaml` -- versioned, diffable, and read **from the
base ref**, never from the tree under judgement. The rule is the same one
`bin/diff-intake` uses for `policy/agent-diff-forbidden.txt`: a gate that reads its own policy
from the workspace it is judging can be weakened in the same change that touches the guarded
paths. The test `test_the_change_cannot_weaken_the_inventory_it_touches` proves it.

The inventory is seeded from code, not from taste:

| id | kind | source of the paths |
|----|------|---------------------|
| `fleet-surface` | founder_surface | `probes/surfaces.py` (`/fleet`, `/face`, the room panel, the backend that serves them) |
| `voice-surface` | founder_surface | `packages/voice/`, the Python SDK, the chrome extension, `factory/surfaces/voice.py` |
| `founder-decision-door` | founder_surface | `sovereign/otto/`, `bin/founder-decision` -- the one place "the founder said yes" is defined |
| `executor-door` | critical_service | `mcp/plugins/`, `platform/executor/` -- the only door every agent passes through |
| `merge-lane` | critical_service | `greenlane/`, `.github/workflows/` -- the only path to main |
| `governance` | critical_service | the laws, the registry, the intents, `policy/`, the hook infrastructure |
| `routing` | critical_service | `llm/`, `litellm-local/` -- the router decides which model answers |
| `deployment` | critical_service | `deploy/`, `clusters/`, `scheduler/`, `installer/` -- what Flux converges on |

`policy/agent-diff-forbidden.txt` already carries a broader, human-maintained critical-path
inventory. It is evidence, not the gate: it governs the separate `~/agent-diffs/<name>` intake
path, and its list is deliberately wider than "changing this can take the founder down". The two
lists overlap on purpose and disagree on purpose; neither replaces the other.

## Fail closed: the inventory of unknowns

Every way of not knowing is a refusal. This is the same rule the guarded-path repair applies,
and the same rule `bin/idp-ci-guarded-paths` learned the hard way on 2026-10-30 (its diff was
uncomputable, the failure was swallowed, and the founder-signature requirement never fired
once in a month):

| unknown | outcome |
|---------|---------|
| the base ref does not resolve | refuse |
| the changed-file set cannot be computed | refuse |
| the inventory is missing, unreadable or declares no surfaces | refuse |
| a guarded path is touched and there is no receipt | refuse |
| the receipt is for a different commit | refuse (replay) |
| the receipt was taken against a different base | refuse (it covered other changes) |
| the receipt is malformed | refuse |
| the receipt's digest does not match its contents | refuse (it was edited after the fact) |
| the receipt says "pass" but carries a high or critical finding | refuse (the receipt contradicts itself) |
| the receipt says "pass" but Tier 3 verified a finding | refuse (a verified finding is a real finding) |

There is exactly one pass with a receipt: a receipt whose digest matches, whose `sha` is the
commit under judgement, whose `base` is the merge base, whose verdict is `pass`, and which
carries no blocking finding.

## The receipt

```json
{
  "schema": "estate.review-receipt.v1",
  "sha": "<the reviewed commit>",
  "base": "<the merge base it was reviewed against>",
  "verdict": "pass",
  "tiers": ["t0", "t1", "t2", "t3"],
  "findings": {"critical": 0, "high": 0, "medium": 2, "low": 5},
  "verified": 0,
  "generated_at": "2026-10-30T12:00:00Z",
  "digest": "sha256:<over every other field, canonical json, sorted keys>"
}
```

The digest is what makes the receipt unforgeable-by-accident and tamper-evident: editing the
verdict or a finding count without re-computing the digest breaks the receipt, and the gate
refuses it.

**Where the receipt must come from.** The receipt has to be produced in CI, on the head SHA, and
carried as a CI artifact. A receipt an agent writes into its own workspace is a note to itself,
not evidence, and no digest makes it otherwise: the gate can prove the receipt is *intact*, and
only CI can prove it is *real*. That is why the wiring decision below puts the review job and
the gate job in the same workflow, with the receipt passed between them as an artifact.

## The enforcement decision, and what is deliberately not done yet

Three wirings were considered:

1. **A `laws.yaml` law with a `command` check.** The law machinery already runs
   `bin/estate-law-gate` as a blocking CI job, and `platform/estate/governance/checks.py`
   supports a `command` check whose exit status is the verdict. This is the cheapest wiring and
   it inherits the law framework's own falsifier discipline.
2. **A dedicated `bin/idp-review-gate` job in `ci-success`.** `ci-success` is the one check the
   merge queue gates on, so a failure here actually stops a merge.
3. **Both.**

The decision is **both, in this order**: the `laws.yaml` law carries the *policy* (a change to a
guarded path must carry a passing receipt) and runs the gate as its command check; `ci-success`
carries the *gate itself* as a required check, so the merge queue refuses. The law alone would
be enough to block a PR but would be one of many jobs; the `ci-success` job is the one the queue
watches.

**Not done in this slice, on purpose.** The decision core, the inventory and the falsifiers are
landed and proven. The wiring is not, for two reasons that are not about effort:

* The receipt writer (`bin/idp-review-receipt`) and the CI review job do not exist yet, and a
  gate that is wired to a receipt nobody produces is a gate that refuses everything -- which
  would block the estate's own work. Wiring without the writer is a red CI, not a gate.
* The estate's own rule is that a change to the governance layer and the CI workflows is
  reviewed too. This change is itself a change to `platform/estate/governance/**`, so under the
  rule this document proposes, it needs a receipt before it lands. That is the intended
  behaviour, and it is applied here by hand: the review receipt for this change is produced by
  running the four-tier pipeline over the branch and is attached to the claim, not manufactured
  by hand.

So the slice lands: the inventory, the decision core, the falsifiers, and this document. The
next slice lands the writer, the CI job and the law, and only then does the gate become
blocking.

## Falsifiers (all landed, all green)

`tests/test_forced_review_gate.py`, 21 tests, in a real git fixture:

* known-bad: a guarded change with no receipt is refused;
* known-bad: a receipt for another commit is refused (replay);
* known-bad: a receipt for another base is refused;
* known-bad: a receipt edited after the fact is refused (digest);
* known-bad: a receipt claiming `pass` while carrying a high finding is refused (anti-lie);
* known-bad: a receipt claiming `pass` while Tier 3 verified a finding is refused;
* known-bad: a failing receipt is refused;
* known-bad: a malformed receipt is refused;
* known-bad: a missing inventory is refused, not passed;
* known-bad: an unresolvable base is refused, not passed;
* known-bad: a change that edits the inventory and the guarded path together is still refused;
* known-good: a guarded change with a matching, passing receipt is allowed;
* known-good: a change that touches nothing guarded needs no receipt.

## What this gate does not do

* It does not review code. The four-tier pipeline does that; the gate only asks whether the
  review happened and passed.
* It does not replace the founder signature. The seven signed paths keep requiring the founder;
  this gate covers a wider set with a cheaper authority.
* It does not block diagnostics. A change to a critical service still needs a review; an agent
  still needs to be able to read, diagnose and repair.
* It does not judge severity of intent. It judges paths and receipts. A malicious change to a
  founder surface with a passing review is a review failure, and the review pipeline is where
  that must be caught.

## If the founder dislikes this

The inventory is one YAML file with eight entries; delete an entry and the gate covers less.
The decision core is one module with no imports outside the standard library and PyYAML. The
receipt format is one JSON document. Nothing here is load-bearing for the executor, the lane or
the runtime, so the whole slice can be removed without touching anything else.

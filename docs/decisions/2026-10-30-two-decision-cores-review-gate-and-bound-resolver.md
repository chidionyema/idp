# Two decision cores: the forced-review gate and the adaptive bound resolver

Status: accepted, cores landed, wiring deferred to a named next slice.
Date: 2026-10-30.
Claim: chidionyema/idp#7544.
Agent: pi-design-cores.

## The decision

We land two pure decision cores and their falsifiers now, and we do **not** wire either into
the CI pipeline in the same change.

1. `platform/estate/governance/review_gate.py` -- decides whether a change that touches a
   founder surface or a critical service may land without a passing review receipt.
   Design: `docs/designs/2026-10-30-forced-review-gate.md`.
2. `platform/executor/bounds.py` -- decides what a string timeout bound means and what the door
   should do about it: allow, route, deny, or allow-unknown.
   Proposal: `docs/proposals/2026-10-30-adaptive-executor-timeout-bounds.md`.

Both are accompanied by a machine-readable inventory (or vocabulary), a test file with
load-bearing falsifiers, and a document that states exactly what is not done.

## Why the cores land before the wiring

A gate that is wired to a producer that does not exist yet refuses everything. A resolver that
is wired into the door without a receipt writer learns from nothing and grants nothing. Both
would be red pipelines that look like governance and are actually breakage.

There is a second reason, and it is the estate's own law applied to ourselves. The forced-review
inventory classifies `platform/estate/governance/**` and `platform/executor/**` as critical
services. So the change that introduces the gate is itself a change that touches a critical
service. Under the rule this decision adopts, it needs a review receipt before it lands. Wiring
it in the same commit would mean the gate is enabled by the very commit it is supposed to
police, with no receipt and no chance to refuse -- the definition of a gate that cannot fail.

So: land the core, prove it, and let the wiring be a separate change that carries its own
receipt. The cost of this choice is one slice of delay. The benefit is that the first
enforcement of the rule is an enforcement that could actually refuse.

## The two cores do not overlap

* The review gate asks *may this change land?* It reads a repository and a receipt. It never
  calls the executor, never runs a review, never touches the clock.
* The bound resolver asks *how long may this command take?* It reads a string and a list of
  receipts. It never runs a command, never touches git, never touches the network.

Neither imports the other. Both are importable without side effects and are exercised by
pytest without a daemon, a cluster or a network.

## The shared rule

Both cores state the same rule in their own terms: **an unknown is not a pass.**

* The gate refuses when it cannot read the inventory, cannot compute the diff, cannot find the
  receipt, cannot verify the digest, or finds a receipt that contradicts itself.
* The resolver returns `UNKNOWN` with a conservative bound when it has no measurement, and
  `DENY` when the request cannot be parsed. It never returns the maximum because nothing was
  known.

Both rules were learned the same way: from a gate that failed open. The guarded-path checker
swallowed its diff failure and the founder-signature requirement never fired; the pre-push hook
classified a Gherkin file as a script and refused a legitimate change. A gate that cannot fail
is not a gate, and a gate that cannot tell is not allowed to say yes.

## The pieces that are deliberately missing, and where they go

| missing piece | where it goes | why it is not here |
|----------------|---------------|--------------------|
| the review receipt writer (`bin/idp-review-receipt`) | the governance slice | it must read the four-tier pipeline's own output; the pipeline's output format is not yet contractual |
| the CI review job that produces the receipt on the head SHA | `.github/workflows/` | a receipt an agent writes for itself is a note, not evidence |
| the `laws.yaml` law carrying the policy | `platform/estate/governance/laws.yaml` | the law needs the writer, or it refuses everything |
| the `ci-success` job carrying the gate | `.github/workflows/` | same |
| the executor's elapsed-time receipt | `platform/executor/run.py` | **landed 2026-10-30** with the executor's own tests -- `docs/decisions/2026-10-30-the-executor-records-what-it-measured.md` |
| the command-shape fingerprint | `platform/executor/` | **landed 2026-10-30** with the receipt; the shape is the executable plus the flag names, values redacted |
| the door's use of the resolver | `mcp/plugins/estate_executor.py` | the door is the hottest code in the estate and it changes under its own claim |
| the routing of `need:N` to `background` / `session` / `lane` | the executor and the session plane | routing is a placement decision and belongs to the placement ladder, not to a resolver |

Each of these is a named, bounded slice with its own issue, claim, tests and falsifiers. Naming
them here is the point: an unbounded "we will wire it later" is how the estate grows a second
copy of everything.

## The governance note

This work was claimed as issue `chidionyema/idp#7544` while the SF-2/SF-3 claim `#7342` was
still live but blocked on a founder decision that has not arrived. The two claims hold disjoint
paths and the claim gate reported no overlap. It is still a deviation from the
one-capability-at-a-time rule, it was taken deliberately (the founder asked for both
deliverables, and the blocked capability is blocked on a human, not on work), and it is recorded
here rather than buried.

# A memory write earns its rung, and the gate asks the door on the wire

**Date:** 2026-10-26
**Status:** accepted
**Amends** the trust model in the estate-memory spec and the rungs in `bin/memory-gate`.

## The problem

An agent's memory write arrived in the store labelled `raw_source`. Everything did: measured on
2026-10-26, the shared store held 193 memories and **193 carried `source = raw_source`**, because
the door every agent writes through — `remember` on the estate-mcp server — had no argument for
what the agent had measured. The write could not be wrong about its evidence, because it could
not carry any.

Two things followed, and they are the same thing:

1. **Nothing was graded.** `bin/memory-gate` proves the estate *can* grade a write: it runs the
   door's own functions inside the pod, checks the rung the store labels the row with, and holds
   the brief. But a gate that grades a write the gate itself composed says nothing about the
   writes agents actually make. The estate was green in one agent's hands and ungraded in
   everybody else's.
2. **The brief asserted.** The block above the memories was headed `VERIFIED` regardless of what
   it contained, so an agent reading it inherited a claim no measurement backed.

Measured root cause of both: the grading code was on `main` (#7166, #7170) and the cluster ran
`estate-mcp:main-14831` from August, whose `tools/list` advertised `content`, `kind`, `runtime`,
`source`, `subject`, `tags` — and no `instrument`, `evidence` or `authority` — and whose plugin
had no `claim_checker` at all (`bin/memory-gate` failed at rung 3 with `AttributeError: module
'em' has no attribute 'claim_checker'`).

## The decision

**The write carries what it measured; the store labels the row; the gate asks the door.**

1. `remember` takes `instrument`, `evidence` and optional `authority`. A write with no evidence
   still succeeds — it is honest work, just unevidenced — and comes back `raw_source`.
2. The store labels the row by that evidence and returns the rung and the trust tier in the
   reply, so the agent that wrote it learns what its own write earned.
3. `bin/memory-gate` gains a rung that **asks the live door on the wire**: it reads the pod's
   `tools/list` and fails unless `remember` can be handed the evidence. Rungs 2 and 3 call the
   plugin's own functions inside the pod, so they pass even when the advertised schema cannot
   carry a measurement — the schema is what every other agent sees, so it is the thing that has
   to be checked. (`bin/memory-door-schema` is that check on its own, so it can be run against a
   pod without running the whole gate.)
4. The wire probe is **read-only**. `remember` takes no namespace argument, so a wire *write*
   would land in the shared `estate` namespace and rank against real memories. The write path is
   graded by rung 3, which performs and inspects a write marked as the gate's own.

## What this rules out

- **Grading a synthetic probe.** A probe proves the door works when called the way the probe
  calls it. The question is what a real agent's call carries.
- **Grading the repo's config offline.** Reading `mcp/plugins/estate_memory.py` in the checkout
  proves what *main* says, not what the running pod advertises — and the gap between those two
  was exactly the defect.
- **Stamping `VERIFIED` on an ungraded brief.** The header now states what was measured and how
  much of the store carries evidence; an all-`raw_source` store says so.

## Consequences

- Every agent's write is graded by the same checker, with no change to how an agent calls the
  door: evidence is optional, absence is reported rather than refused.
- The 193 historical `raw_source` rows stay `raw_source`. They are true: nobody measured them.
- A roll is now part of the contract. Code on `main` that no pod runs is not a capability, so
  the pins in `platform/mcp/kustomization.yaml` and
  `platform/unified-memory-server/kustomization.yaml` are the difference between shipped and
  operating, and a rung that asks the live door is what notices when they drift.

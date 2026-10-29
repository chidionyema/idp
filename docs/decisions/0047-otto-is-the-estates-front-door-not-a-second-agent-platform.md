# 0047 — Otto is the estate's front door, not a second agent platform

**Date:** 2026-10-29
**Status:** proposed (founder ratification pending) — companion spec
`docs/specs/2026-10-29-otto-is-the-estates-front-door.md`, issue chidionyema/idp#7408
**Decider:** the founder (instruction of 2026-10-29), recorded by `pi`
**Extends:** 0022 (voice first), 0024 (Otto runs every tool), 0036 (one memory plane),
0039 (one mouth), 0043 (the bound lives at the door)
**Relates to:** `docs/epics/2026-10-28-otto-minimum-viable-programme.md` (the audit that asked
the question), `docs/specs/otto-answering-floor.md` (the rules this decision extends one layer
down)

---

## Context

Otto has been in the estate for three months. It has a real Telegram door, a real seam, a real
thread, real presence, real media handling and a real answer probe. It also has a second
router, a second memory plane, a second tool registry, a second verification plane and a second
set of lane values.

The founder's instruction of 2026-10-29 was to reconstruct the vision from the record, judge
the architecture, and re-propose so the concept and the architecture are unambiguous. The
specification that answers it is the spec above. This record is the decision.

The short history is in the spec's §3. In one line: **each founder wish was answered locally,
inside Otto, and no global constraint was ever applied to the parts as a set.** ADR 0036
(2026-10-02) already decided that Otto's memory planes are deleted — twenty-seven days later
the manifests still point at hindsight. A decision that is only a document does not move a
manifest; that is the lesson this record exists to make permanent.

## Decision

**Otto is the estate's front door.** Everything a human says to the estate, and everything the
estate needs a human to say, crosses Otto. Below the seam, Otto owns nothing: it borrows the
estate's one router, one memory, one executor, one verifier, one identity and one secret store.
The seam is where new surfaces come from; the layers below it never multiply.

### Clauses

**D1 — The seam is the product, and it stays.** A surface is one binding and one registry row
(`docs/specs/otto-answering-floor.md:23`). The gateway does not change to add a surface. Otto
keeps the thread, the trust classes, the presence, the media pipeline, the reply delivery and
the channel registry: they are the surface layer, they are measured, and they are the only part
of three months of Otto that other work in this estate depends on.

**D2 — Below the seam, Otto borrows.** Routing, memory, execution, verification, identity,
secrets and evidence are the estate's. Otto calls them through their doors. Concretely:
the estate's cloud router is the default route; `remember`/`recall` is the only memory;
estate-affecting actions go through intents, `estate-execute` and the claim gate; the doctor
family owns the verdict on Otto's health; OIDC and the vault stay where they are.

**D3 — The lifeboat stays, and it is last.** A1–A4 of the founder's wishes are real and are
satisfied by a loopback litellm in Otto's pod with no policy and no ledger: when the router is
unreachable, Otto still answers. What changes is that the lifeboat is no longer the *default*.
The default is the estate's one router, on the cloud route (`https://llm.${ESTATE_ZONE}`),
which is outside the cluster's failure domain. Two transports is the price of "never be
silent"; two routers is not, and was never what the founder asked for. A turn the lifeboat
answers is accounted to the estate's ledger by the `router.outcome` event Otto already emits —
availability outranks the *accounting of the wrong thing*, not the absence of accounting.

**D4 — Otto's memory planes are deleted, per ADR 0036.** `otto_facts`,
`otto/memory/fast_recall.py`, the hindsight URL, the `otto-memory-store` Job and Otto's own
embedding path all go. Writes move to `remember`. This decision adds nothing new here; it
makes ADR 0036 enforceable, and names the gate that enforces it. The estate has ordered this
work already and it has not moved: idp#6162 ("import Hindsight, then retire it"), idp#6163
("delete the duplicate memory layers"), idp#6229 and idp#6165 are all open against a decision
from 2026-10-02.

**D5 — A model-driven shell never runs beside a secret.** `terminal` and `code_execution` move
out of the container that holds the bot token, the DB password and the GitHub token, into the
secretless `otto-sandbox` Job specified in
`docs/specs/otto-door-hands-and-senses.md:200-203`. ADR 0024 stands: Otto still runs every
tool unattended and asks only for the unundoable.

**D6 — One verification plane.** Otto's answer probe, its registration reconciler and the
`otto-parity` tick stop deciding whether Otto is healthy. The estate's doctor family decides
(`telegram-agent.doctor`, landed in #7361/#7380/#7386); the probe and the tick become inputs it
reads. The probe keeps asking the real lane — that is its job — but a probe that grades a lane
the door no longer uses is not an instrument.
The estate's own principle is the reason: a verdict must be "produced by a process the agent
cannot run" (`docs/explanation/verification-plane.md`, crew#631). Otto's own probe cannot certify
Otto; that is what self-certification means.

**D7 — The human-in-the-loop plane is Otto's, and it is new.** When an agent is blocked it
reaches a human **through Otto**, by voice or Telegram, with the blocker, the claim and the
approval path named (#7388). A structured decision is answered as a record, not as a message
that evaporates (#7384, #7340). No approval path may require the founder to be at a laptop.

**D8 — One shared value, one place.** Every value that both the door and a probe read comes
from one source, the way `platform/otto-gateway/router-lanes.yaml` fixed the lane drift that
happened twice. Otto's manifest may not restate an estate value.

**D9 — A manifest that names an estate layer is refused.** A conformance gate reads
`platform/otto-gateway/*.yaml` and fails when a manifest names a layer the estate owns (a
hindsight or `otto_facts` URL, a loopback `LITELLM_BASE_URL` that is not the last rung, a shell
in a secret-holding container, a vendor key duplicated from the vault). The rule is a table, so
it is checkable, and the gate can fail.

### What this decision refuses

- It does not remove a surface, a binding, a thread, a probe, or the lifeboat.
- It does not add a service, a store, a router, or a gate that cannot fail.
- It does not touch `AGENTS.md`, the lane values, the founder's vault, or the cluster by hand.
- It does not claim any of it is operating. The waves and their proof obligations are in the
  spec; none of them is done.

## Alternatives considered

**Keep Otto as it is, and just fix the bugs.** Rejected: the bugs are the shape. A second
router, a second memory and a second verification plane are not defects in an implementation;
they are three answers to three wishes that were never reconciled with the estate's layers.

**Make Otto the platform and move the estate's layers into it.** Rejected: it contradicts the
estate's law of one-of-each-layer (AGENTS.md §6) and it would put the founder's Telegram
availability on the same plane as the estate's execution boundary, memory and secrets. The
seam already works; the layers below it do not need to move.

**Delete Otto's private planes and let the estate's doors serve the founder directly.** Rejected:
the founder's Telegram presence, the thread and the escalation path are real product, and
removing them would delete the one thing three months of Otto built that the estate wants.

**Keep the lifeboat as the default and accept the accounting gap.** Rejected by the founder's
own ruling of 2026-10-26: the cloud route is the default. The availability wish is satisfied by
the cloud route plus the lifeboat, not by the lifeboat alone.

## Consequences

**Positive.** One router, one memory, one execution boundary, one verifier, one identity, one
secret store — and a front door that can add surfaces forever without touching any of them.
The founder's Telegram stays the front door; the estate's layers become reachable from it. The
audit's root cause RC1 ("Otto was asked to be an agent, and told to dispatch") is answered by
naming what Otto is instead: not a dispatcher of the estate's capabilities, and not a second
agent platform — the estate's human-facing surface, standing on the estate's own layers.

**Negative, accepted.**

1. **The lifeboat becomes rare.** If the cloud router is healthy, the lifeboat is never used —
   and a rarely exercised path is a path that breaks silently. Mitigated: the doctor reads the
   lifeboat's health, and the routing decision is re-measured, not assumed.
2. **Waves 1–3 land before anything is visible.** The founder sees no new surface while this
   decision is implemented. Accepted: the alternative is another three months of surfaces over
   a duplicated platform.
3. **Otto's private memory and lane values disappear from the codebase.** Anything that read
   them directly breaks. That is the point, and it is the reason the waves are ordered.
4. **The estate's executor becomes Otto's hands.** Otto's actions are slower and more gated
   than a direct pod-local call. Accepted: the gate is the feature (ADR 0024 asks only for the
   unundoable; the claim gate is what makes unattended work safe).
5. **The eval the founder asked for gets a shape.** idp#6921 ("beat Muse") wants a BDD and an
   eval harness that proves Otto beats a baseline. This decision does not build it, but it fixes
   its shape: the graded surface is the estate's door, the baseline runs through the same door,
   and the harness is the estate's — a private grader inside Otto would measure Otto against
   itself.

## Enforcement

The gates are named in the spec §8: a new manifest-conformance gate; the `router-lanes.yaml`
pattern for every shared value; `bin/memory-gate`; `telegram-agent.doctor`; the claim gate.
A decision without a gate that can fail is a wish. This one has five.

## Supersedes and is superseded by

- **Supersedes in part:** nothing. ADR 0036 already decided the memory clause; this record
  makes it enforceable. The three-homes design's *stated* intent ("the estate keeps one router
  and home 1 is it") is restored as the default; its *current* implementation (free lanes
  heading every chain) is superseded by D3.
- **Superseded by:** nothing yet.
- **Related:** ADR 0022 (voice first, nothing is deleted), 0024 (hands), 0033 (edge voice is the
  target), 0036 (one memory plane), 0039 (one mouth), 0043 (the bound lives at the door),
  AGENTS.md §6 (one of each layer) and §7a (cloud is the default route).
